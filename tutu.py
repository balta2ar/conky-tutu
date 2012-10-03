#!/usr/bin/env python

import sys
import time
import datetime
import argparse
import urllib.parse
import urllib.request
from html.parser import HTMLParser

TUTU_REQUEST = 'http://www.tutu.ru/rasp.php?%s'
ARGS = None

# create a subclass and override the handler methods
class TutuParser(HTMLParser):
    def __init__(self, parse_date):
        """
        seq_started - function which looks at the tag data and tells whether
                      it starts the sequence
        seq_len     - length of the sequence
        """
        HTMLParser.__init__(self)
        self.tag_data = ''
        self.in_tag = False
        self.parse_date = parse_date
        self.seq_len = 4
        self.seq_n = 0
        self.schedule = []
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
                    self.travel = {'departure_time': date}
            elif self.seq_n == self.seq_len - 1:
                self.travel['arrival_time'] = date
                if date < self.travel['departure_time']:
                    # arrives next day
                    date += datetime.timedelta(days=1)
                ttime = date - self.travel['departure_time']
                self.travel['mins_in_travel'] = int(ttime.total_seconds() / 60)
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
    max_dep_st = max([len(t['departure_station']) for t in schedule])
    max_arr_st = max([len(t['arrival_station']) for t in schedule])
    lines = [travel_to_str(t, max_dep_st, max_arr_st) for t in schedule]
    return '\n'.join(lines)

def travel_to_str(t, mdep, marr):
    tformat = '%H:%M'
    template = '{} {} {:3>} {:{lalign}{lfill}} -> {:{ralign}{rfill}}'
    ARGS = [t['departure_time'].strftime(tformat)
          , t['arrival_time'].strftime(tformat)
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
    #print(save_schedule(download_schedule()))
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
    print(ARGS)

    process()
    return 0

if __name__ == '__main__':
    sys.exit(main())
