conky-tutu
==========

conky config + python3 script for viewing schedule from [tutu.ru][1]
---------------------------------------------------------------------

### Screenshots

![conky-tutu screenshot](http://i.imgur.com/nQvZz.png "Screenshot")

### Usage

    $ ./tutu.py --help
    usage: tutu.py [-h] [-dsn DEP_STATION_NAME] -dsc DEP_STATION_CODE
                        [-asn ARR_STATION_NAME] -asc ARR_STATION_CODE
                        [-cf CACHE_FILE] [-d DATE]
                        [-wr WITHIN_RANGE | -wt WITHIN_TIME]

    Download, parse and prepare for conky tutu schedule.

    optional arguments:
      -h, --help            show this help message and exit
      -dsn DEP_STATION_NAME, --dep-station-name DEP_STATION_NAME
                            Departure station name
      -dsc DEP_STATION_CODE, --dep-station-code DEP_STATION_CODE
                            Departure station code
      -asn ARR_STATION_NAME, --arr-station-name ARR_STATION_NAME
                            Arrival station name
      -asc ARR_STATION_CODE, --arr-station-code ARR_STATION_CODE
                            Arrival station code
      -cf CACHE_FILE, --cache-file CACHE_FILE
                            Cache file name
      -d DATE, --date DATE  Date of schedule
      -wr WITHIN_RANGE, --within-range WITHIN_RANGE
                            Range of time between trips: N,M - number of trips
                            to show before and after the nearest trip
      -wt WITHIN_TIME, --within-time WITHIN_TIME
                            Range of time between trips: N,M - time range trips
                            to show before and after the nearest trip in
                            format %H:%M

### Configuration

The only mandatory arguments are `--dep-station-code` and `--arr-station-code`.
You need to obtain these codes on [tutu.ru][1] once and use them in the script
thereafter. Values of `--dep-station-name` and `--arr-station-name` are put
into header.

The script does not download schedule every time you run it. Instead, it
downloads it if cache file is missing or if its `mtime` is too old. "Too old"
means that it was modified another day (not today).

It is likely that you want to see schedule for both directions. Second conky
instance will help you in this case. Make sure to make the following changes in
the second conky config file:

1. Swap `-asc` and `-dsc` arguments
2. Specify different `--cache-file` for each conky instance (you don't want them
   to overwrite each other, right?)

Default script output is usually too long and not very useful. The output can be
reduced with either of two arguments: `--within-range` or `--within-time`.  With
`--within-range` you can specify the number of schedule events before and after
the nearest one to the current time, e.g. `--within-range "3, 10"` will leave
three rows before and ten rows after the nearest departure. `--within-time`
expects time intervals (hours:minutes), e.g. `--within-time "1:0, 03:30"` will
only print past departures no older than one hour and future departures no
later than three hours and a half.

Also, you can configure colors for the nearest (current), past and future
departures. See the beginning of the `tutu.py`.

### Copyright

(c) Yuri balta2ar Bochkarev, 2012

[1]: http://www.tutu.ru/prigorod/
