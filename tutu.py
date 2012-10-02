#!/usr/bin/env python

import sys
import time
import datetime
import collections
from html.parser import HTMLParser

Travel = collections.namedtuple('Travel',
    'departure_time arrival_time departure_station arrival_station')

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
    template = '{} {} {:{lalign}{lfill}} -> {:{ralign}{rfill}}'
    args = [t['departure_time'].strftime(tformat)
          , t['arrival_time'].strftime(tformat)
          , t['departure_station']
          , t['arrival_station']]
    return template.format(*args, lalign='>', lfill=mdep,
                                  ralign='<', rfill=marr)

def parse(data):
    # instantiate the parser and fed it some HTML
    parser = TutuParser(parse_date)
    parser.feed(data)
    print(schedule_to_str(parser.schedule))

def process(path):
    with open(path, encoding='utf-8') as f:
        data = f.read()
        parse(data)

if __name__ == '__main__':
    process(sys.argv[1])
