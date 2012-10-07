#!/usr/bin/env python

import os
import sys
import time
import bisect
import datetime
import argparse
import urllib.parse
import urllib.request
from html.parser import HTMLParser

TUTU_REQUEST = 'http://www.tutu.ru/rasp.php?%s'
ARGS = None
COLORS = {
      'prev':    'a67c00' #'#0E2036'
    , 'current': '#adbc93'
    , 'next':    '#7B90A9'
    , 'label':   '#bf9b30'
}

def diff_minutes(t1, t2):
    return int((t1-t2).total_seconds() / 60)

def minutes_to_human(ts):
    return '%02d:%02d' % divmod(ts, 60)

# create a subclass and override the handler methods
class TutuParser(HTMLParser):
    def __init__(self, parse_date):
        HTMLParser.__init__(self)
        self.tag_data = ''
        self.in_tag = False
        self.parse_date = parse_date
        self.seq_len = 4
        self.seq_n = 0
        self.schedule = []
        self.now = datetime.datetime.now()
    def get_schedule(self):
        return sorted(self.schedule, key=lambda x: x['departure_time'])
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.in_tag = True
            self.tag_data = ''
    def handle_endtag(self, tag):
        if tag == 'a':
            self.in_tag = False
            d = self.tag_data.strip()
            date = self.parse_date(d)
            if self.seq_n == self.seq_len - 4:
                if date:
                    # start the sequence
                    self.seq_n = self.seq_len - 1
                    self.trip = {'departure_time': date,
                                   'minutes_remain': diff_minutes(date, self.now)}
            elif self.seq_n == self.seq_len - 1:
                self.trip['arrival_time'] = date
                if date < self.trip['departure_time']:
                    # arrives next day
                    date += datetime.timedelta(days=1)
                self.trip['mins_in_trip'] = diff_minutes(date,
                    self.trip['departure_time'])
                self.seq_n -= 1
            elif self.seq_n == self.seq_len - 2:
                self.trip['departure_station'] = d
                self.seq_n -= 1
            elif self.seq_n == self.seq_len - 3:
                self.trip['arrival_station'] = d
                self.seq_n -= 1
                self.schedule.append(self.trip)
    def handle_data(self, data):
        if self.in_tag:
            self.tag_data += data

def parse_date(s):
    try:
        now = time.localtime()
        t = time.strptime(s, '%H:%M')
        return datetime.datetime(*(now[:3] + t[3:6]))
    except ValueError as e: return None

def filter_schedule(s, flt, pos):
    return [v for (i, v) in enumerate(s) if flt(i, v, pos)]

def make_time_filter(s):
    now = datetime.datetime.now()
    a, b = [x.strip() for x in s.split(',')]
    a, b = datetime.datetime.strptime(a, '%H:%M'), \
           datetime.datetime.strptime(b, '%H:%M')
    a, b = datetime.timedelta(hours=a.hour, minutes=a.minute), \
           datetime.timedelta(hours=b.hour, minutes=b.minute)
    a, b = now-a, now+b
    def f(i, v, pos): return a <= v['departure_time'] <= b
    return f

def make_range_filter(s):
    a, b = [x.strip() for x in s.split(',')]
    a, b = int(a), int(b)
    def f(i, v, pos): return (0 <= pos - i <= a) or (0 <= i - pos <= b)
    return f

def current_pos(schedule):
    now = datetime.datetime.now()
    times = [x['departure_time'] for x in schedule]
    pos = bisect.bisect_left(times, now)
    if pos == len(times): pos -= 1
    return pos

def schedule_to_str(schedule):
    if len(schedule) == 0: return ''

    # find nearest trip
    pos = current_pos(schedule)

    # filter schedule if necessary
    flt = None
    if ARGS.within_range: flt = make_range_filter(ARGS.within_range)
    elif ARGS.within_time: flt = make_time_filter(ARGS.within_time)
    if flt: schedule = filter_schedule(schedule, flt, pos)
    pos = current_pos(schedule)

    # make sure schedule is not empty after filtering
    if len(schedule) == 0: return ''

    max_dep_st = max([len(t['departure_station']) for t in schedule])
    max_arr_st = max([len(t['arrival_station']) for t in schedule])
    lines = [trip_to_str(t, max_dep_st, max_arr_st) for t in schedule]

    # build header
    width = max([len(x) for x in lines])
    h = '%s → %s' % (ARGS.dep_station_name, ARGS.arr_station_name)
    header = '{:^{width}}'.format(h, width=width)

    # build footer
    d = datetime.datetime.fromtimestamp(os.path.getmtime(ARGS.cache_file))
    d = d.replace(microsecond=0)
    footer = '{:^{width}}'.format('Last schedule refresh: %s' % str(d), width=width)

    # build colorized body
    before, current, after = lines[:pos], \
        lines[pos] if pos != len(schedule) else '', \
        lines[pos+1:]
    before = ['${color %s}%s${color}' % (COLORS['prev'], x) for x in before]
    if current: current = '${color %s}%s${color}' % (COLORS['current'], current)
    after = ['${color %s}%s${color}' % (COLORS['next'], x) for x in after]

    # join results
    lines = [header] + before + [current] + after + [footer]
    return '\n'.join(lines)

def trip_to_str(t, mdep, marr):
    tformat = '%H:%M'
    template = '{} {} {:>3} {:>3} {:{lalign}{lfill}} → {:{ralign}{rfill}}'
    rem = t['minutes_remain']
    rem = minutes_to_human(rem) if rem >= 0 else '     '
    ARGS = [t['departure_time'].strftime(tformat)
          , t['arrival_time'].strftime(tformat)
          , rem
          , t['mins_in_trip']
          , t['departure_station']
          , t['arrival_station']]
    return template.format(*ARGS, lalign='>', lfill=mdep,
                                  ralign='<', rfill=marr)

def parse(data):
    # instantiate the parser and fed it some HTML
    parser = TutuParser(parse_date)
    parser.feed(data)
    return parser.get_schedule()

def load_schedule(filename):
    with open(filename, encoding='utf-8') as f:
        data = f.read()
        return parse(data)

def print_schedule():
    print(schedule_to_str(load_schedule(ARGS.cache_file)))

def process():
    ex = os.path.exists(ARGS.cache_file)
    old = False
    if ex:
        tm = os.path.getmtime(ARGS.cache_file)
        dt = datetime.datetime.fromtimestamp(tm)
        old = dt.date() != datetime.datetime.today().date()
    if not ex or old: save_schedule(download_schedule())
    print_schedule()

def download_schedule():
    params = {'st1': ARGS.dep_station_code
            , 'st2': ARGS.arr_station_code
            , 'date': ARGS.date
            , 'noblue': 1
            , 'nogreen': 1}
    sparams = urllib.parse.urlencode(params)
    req = urllib.request.urlopen(TUTU_REQUEST % sparams)
    return req.read().decode('utf-8')

def save_schedule(data):
    if data:
        with open(ARGS.cache_file, 'w', encoding='utf-8') as f:
            f.write(data)
        return True
    else: return False

def main():
    parser = argparse.ArgumentParser(description='Download, parse and prepare for conky tutu schedule.')
    parser.add_argument('-dsn', '--dep-station-name', type=str, help='Departure station name', default='From')
    parser.add_argument('-dsc', '--dep-station-code', type=str, help='Departure station code', required=True)
    parser.add_argument('-asn', '--arr-station-name', type=str, help='Arrival station name', default='To')
    parser.add_argument('-asc', '--arr-station-code', type=str, help='Arrival station code', required=True)
    parser.add_argument('-cf', '--cache-file', type=str, help='Cache file name', default='tutu.html')
    parser.add_argument('-d', '--date', type=str, help='Date of schedule', default='today')
    within = parser.add_mutually_exclusive_group()
    within.add_argument('-wr', '--within-range', type=str, help='''Range of
        trips: N,M - number of trips to show before and after the
        nearest trip''', default=None)
    within.add_argument('-wt', '--within-time', type=str, help='''Range of
        trips: N,M - time range trips to show before and after the
        nearest trip in format %%H:%%M''', default=None)

    global ARGS
    ARGS = parser.parse_args()

    process()
    return 0

if __name__ == '__main__':
    sys.exit(main())
