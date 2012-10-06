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
      'prev':    '#a67c00'
    , 'current': '#ffdc73'
    , 'next':    '#ffcf40'
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
                    self.travel = {'departure_time': date,
                                   'minutes_remain': diff_minutes(date, self.now)}
            elif self.seq_n == self.seq_len - 1:
                self.travel['arrival_time'] = date
                if date < self.travel['departure_time']:
                    # arrives next day
                    date += datetime.timedelta(days=1)
                self.travel['mins_in_travel'] = diff_minutes(date,
                    self.travel['departure_time'])
                self.seq_n -= 1
            elif self.seq_n == self.seq_len - 2:
                self.travel['departure_station'] = d
                self.seq_n -= 1
            elif self.seq_n == self.seq_len - 3:
                self.travel['arrival_station'] = d
                self.seq_n -= 1
                self.schedule.append(self.travel)
    def handle_data(self, data):
        if self.in_tag:
            self.tag_data += data

def parse_date(s):
    try:
        now = time.localtime()
        t = time.strptime(s, '%H:%M')
        return datetime.datetime(*(now[:3] + t[3:6]))
    except ValueError as e: return None

def schedule_to_str(schedule):
    schedule = schedule[30:]
    max_dep_st = max([len(t['departure_station']) for t in schedule])
    max_arr_st = max([len(t['arrival_station']) for t in schedule])
    lines = [travel_to_str(t, max_dep_st, max_arr_st) for t in schedule]

    # build header
    width = max([len(x) for x in lines])
    h = '%s -> %s' % (ARGS.dep_station_name, ARGS.arr_station_name)
    header = '{:^{width}}'.format(h, width=width)

    # build footer
    d = datetime.datetime.fromtimestamp(os.path.getmtime(ARGS.cache_file))
    d = d.replace(microsecond=0)
    footer = '{:^{width}}'.format('Last refresh: %s' % str(d), width=width)

    # find nearest travel
    now = datetime.datetime.now()
    times = [x['departure_time'] for x in schedule]
    pos = bisect.bisect_right(times, now)

    # build colorized body
    before, current, after = lines[:pos], \
        lines[pos] if pos != len(times) else '', \
        lines[pos+1:]
    before = ['${color %s}%s${color}' % (COLORS['prev'], x) for x in before]
    if current: current = '${color %s}%s${color}' % (COLORS['current'], current)
    after = ['${color %s}%s${color}' % (COLORS['next'], x) for x in after]

    lines = [header] + before + [current] + after + [footer]
    return '\n'.join(lines)

def travel_to_str(t, mdep, marr):
    tformat = '%H:%M'
    template = '{} {} {:>3} {:>3} {:{lalign}{lfill}} -> {:{ralign}{rfill}}'
    rem = t['minutes_remain']
    rem = minutes_to_human(rem) if rem > 0 else '     '
    ARGS = [t['departure_time'].strftime(tformat)
          , t['arrival_time'].strftime(tformat)
          , rem
          , t['mins_in_travel']
          , t['departure_station']
          , t['arrival_station']]
    return template.format(*ARGS, lalign='>', lfill=mdep,
                                  ralign='<', rfill=marr)

def parse(data):
    # instantiate the parser and fed it some HTML
    parser = TutuParser(parse_date)
    parser.feed(data)
    print(schedule_to_str(parser.schedule))

def print_schedule():
    with open(ARGS.cache_file, encoding='utf-8') as f:
        data = f.read()
        parse(data)

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
    parser.add_argument('-dsn', '--dep-station-name', type=str, help='departure station name', default='From')
    parser.add_argument('-dsc', '--dep-station-code', type=str, help='departure station code', required=True)
    parser.add_argument('-asn', '--arr-station-name', type=str, help='arrival station name', default='To')
    parser.add_argument('-asc', '--arr-station-code', type=str, help='arrival station code', required=True)
    parser.add_argument('-cf', '--cache-file', type=str, help='cache file name', default='tutu.html')
    parser.add_argument('-d', '--date', type=str, help='date', default='today')

    global ARGS
    ARGS = parser.parse_args()
    #print(ARGS)

    process()
    return 0

if __name__ == '__main__':
    sys.exit(main())
