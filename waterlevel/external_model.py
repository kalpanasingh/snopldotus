from django.conf import settings

import types
import json
import httplib
import pprint
import datetime
from datetime import date, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# hard-coded assumptions:
FTB = 0
TOP_LEVEL = 76  # Top of cavity in feet
MID_LEVEL = 40  # Middle of cavity in feet
FEET_PER_SHIFT_OPT = 0.5  # Optimistic number of feet per shift
FEET_PER_SHIFT_PES = 0.341667  # Pessimistic number of feet per shift
# If you change the date to an ealier date, make sure to change the skip-values
# when contacting the DB.
START_DATE = "2016-07-15 00:00:00"  # From what date to start the plot
#END_DATE = "2016-01-01 00:00:00"  # To what date to plot
TENSION_START_DATE = "2016-07-15 00:00:00"  # Start date for tension data?
PROJECTION_DATE = "2015-11-19 00:00:00"  # Date to keep projection estimate
PROJECTION_LEVEL = 0.0  # Level to start projection from
AV_CONVERSION = 2.31  # Conversion factor for the AV PI server readout

def convert_date(datestring):
    if "T" in datestring:
        try:
            dt = datetime.datetime.strptime(datestring, '%Y-%m-%dT%H:%M:%S.%f')
        except ValueError:
            dt = datetime.datetime.strptime(datestring, '%Y-%m-%dT%H:%M:%S')
        return dt
    if "." in datestring:
        return datetime.datetime.strptime(datestring, '%Y-%m-%d %H:%M:%S.%f')
    return datetime.datetime.strptime(datestring, '%Y-%m-%d %H:%M:%S')


def couch_request(server, request_url, auth_info=None):
    """ Connect to server, send request_url, return result data """
    request_headers = {'Content-type': "application/json"}
    if auth_info is not None:
        request_headers['Authorization'] = 'Basic {}'.format(auth_info.encode(
            'base64'))
        request_headers['Authorization'] = request_headers['Authorization'].rstrip()

    connection = httplib.HTTPConnection(server)
    connection.request('GET', request_url, headers=request_headers)
    rows = json.loads(connection.getresponse().read())['rows']
    rows = [row['value'] for row in rows]

    return [dict([(key, value) for key, value in rowdict.items()
                  if not key.startswith("_")])
            for rowdict in rows]


def get_historical_waterlevels():
    """ Return a list of entries from the couchdb database """

    data = couch_request(
        settings.WATERLEVEL_SERVER,
        '/water-level/_design/water-level-readings/_view/readings?skip=10100',
        settings.WATERLEVEL_AUTH)
    return [(convert_date(record['time']), record['waterlevel_cavity'],
            record['waterlevel_av']) for record in data
            if (convert_date(record['time']) > convert_date(START_DATE)
            and type(record['waterlevel_av']) is not types.NoneType)]

def get_historical_ropetension():
    """ Return a list of entries from the couchdb database """

    data = couch_request(
        settings.WATERLEVEL_SERVER,
        '/water-level/_design/water-level-readings/_view/readings?skip=10100',
        settings.WATERLEVEL_AUTH)

    return [(convert_date(record['time']), record['tension_hd_ropes'],
             record['tension_hu_ropes']) for record in data
             if convert_date(record['time']) > convert_date(TENSION_START_DATE)]

# Calculate the future water level.
def calculate_future_waterlevels(type, fillrate, startdate, waterlevel_cavity,
                                 waterlevel_av):
    results = list()
    results.append([startdate, waterlevel_cavity, waterlevel_av])
    FTB = 0
    date_point = startdate
    water_point_cavity = waterlevel_cavity
    water_point_av = waterlevel_av

    # Add fixed delay
    if type == 1:
        while True:
            # Start by increasing the date by 1 day
            date_point = date_point+timedelta(days=1)
            # We have a fixed delay for water-fill due to the review process
            # and the installation of the water pipes
            # Adding a delay here when needed
            review_date = convert_date("2014-09-15 00:00:00")
            water_point_cavity = water_point_cavity
            water_point_av = 0
            results.append([date_point, water_point_cavity, water_point_av])
            days_until_review_date = review_date - date_point
            if days_until_review_date < timedelta(days = 1):
                break

    if water_point_cavity is None: water_point_cavity = 0
    while True:
        # Start by increasing the date by 1 day
        date_point = date_point+timedelta(days=1)
        # Find out what day of the week that is
        dayOfWeek = datetime.datetime.weekday(date_point)
        if dayOfWeek == 0 or dayOfWeek == 1 or dayOfWeek == 4:
            # Single shift days
            water_point_cavity = water_point_cavity + fillrate
            water_point_av = 0
        elif dayOfWeek == 2 or dayOfWeek == 3:
            # Double shift days
            water_point_cavity = water_point_cavity + 2*fillrate
            water_point_av = 0
        elif dayOfWeek == 5 or dayOfWeek == 6:
            # Weekends: Do nothing
            water_point_cavity = water_point_cavity
            water_point_av = 0
        else:
            print error
        # Store this point
        results.append([date_point, water_point_cavity, water_point_av])
        # When we reach the top, break! We do not want to flood the crates...
        if water_point_cavity >= TOP_LEVEL:
            break
        # When we are half-way: stop for 14 days for the FTB
        if round(water_point_cavity) == MID_LEVEL and FTB != 1:
            # Jump 14 days ahead..
            date_point = date_point+timedelta(14)
            # Record last water level at this date
            results.append([date_point, water_point_cavity, water_point_av])
            FTB = 1

    return results


def make_plot(output_filename, output_dpi=100, width=1250, height=633):
    historical = get_historical_waterlevels()
    last_date, last_level_cavity, last_level_av = historical[-1]

    #optimistic = calculate_future_waterlevels(0,FEET_PER_SHIFT_OPT, last_date,
    #                                          last_level_cavity,
    #                                          last_level_av)

    #pessimistic = calculate_future_waterlevels(0,FEET_PER_SHIFT_PES, last_date,
    #                                           last_level_cavity,
    #                                           last_level_av)

    #baseline_opt = calculate_future_waterlevels(0,FEET_PER_SHIFT_OPT,
    #    convert_date(PROJECTION_DATE), PROJECTION_LEVEL, 0)

    #baseline_pes = calculate_future_waterlevels(0,FEET_PER_SHIFT_PES,
    #    convert_date(PROJECTION_DATE), PROJECTION_LEVEL, 0)

    #plt.plot_date([mdates.date2num(t[0]) for t in optimistic],
    #              [t[1] for t in optimistic], 'g-', lw=2,
    #              label="Optimistic projection")

    #plt.plot_date([mdates.date2num(t[0]) for t in pessimistic],
    #              [t[1] for t in pessimistic], 'r-', lw=2,
    #              label="Pessimistic projection")

    #plt.plot_date([mdates.date2num(t[0]) for t in baseline_pes],
    #              [t[1] for t in baseline_pes], 'b--', lw=1,
    #              label="Projection from 23 September 2014")

    #plt.plot_date([mdates.date2num(t[0]) for t in baseline_opt],
    #              [t[1] for t in baseline_opt], 'b--', lw=1)

    plt.plot_date([mdates.date2num(t[0]) for t in historical],
                  [t[1] for t in historical], 'k', label="Level cavity")

    plt.plot_date([mdates.date2num(t[0]) for t in historical],
                  [(t[2] * AV_CONVERSION)  for t in historical], 'k', ls='dotted', lw=2, label="Level AV")


    plt.xlabel('Date')
    plt.ylabel('Water Level test [ft]')
    plt.ylim((0,80))
    plt.xlim()
    plt.yticks(fontsize=10)
    plt.xticks(rotation=17, fontsize=10)
    #last_date = calculate_future_waterlevels(1, FEET_PER_SHIFT_PES, last_date,
    #                                          last_level_cavity,
    #                                           last_level_av)[-1][0]
    last_date = last_date + timedelta(days=4)
    plt.xlim((convert_date(START_DATE),last_date))
    lg = plt.legend(loc=0)
    lg.draw_frame(0)
    plt.axhline(80)
    fig = plt.gcf()
    fig.set_size_inches(width / output_dpi, height / output_dpi)
    plt.savefig(output_filename, dpi=output_dpi)
    plt.close()

def get_enddate():
    historical = get_historical_waterlevels()
    last_date, last_level_cavity, last_level_av = historical[-1]

    opt_enddate = calculate_future_waterlevels(1, FEET_PER_SHIFT_OPT, last_date,
                                               last_level_cavity,
                                               last_level_av)[-1][0]

    pes_enddate = calculate_future_waterlevels(1, FEET_PER_SHIFT_PES, last_date,
                                               last_level_cavity,
                                               last_level_av)[-1][0]

    return opt_enddate + ((pes_enddate - opt_enddate) / 2)

def get_current_waterlevel():
    """ Return the last entry from the couchdb database """
    data = couch_request(
        settings.WATERLEVEL_SERVER,
        '/water-level/_design/water-level-readings/_view/readings?&descending=true&limit=1',
        settings.WATERLEVEL_AUTH)
    current_level = [(convert_date(record['time']), record['waterlevel_cavity'],
                     record['waterlevel_av']) for record in data
                     if (convert_date(record['time']) > convert_date(START_DATE)
                     and type(record['waterlevel_av']) is not types.NoneType) ]
    if len(current_level) > 0:
        return current_level[-1]
    else:
        return (convert_date(data[0]['time']), 'N/A', 'N/A')

def make_tension_plot(output_filename, output_dpi=100, width=1250, height=633):
    historical_tension = get_historical_ropetension()

    fig, ax1 = plt.subplots()
    ax1.plot_date([mdates.date2num(t[0]) for t in historical_tension],
                  [t[1] for t in historical_tension], 'g-', lw=2, label="Tension HD ropes")
    ax1.set_xlabel('Time')
    # Make the y-axis label and tick labels match the line color.
    ax1.set_ylabel('Tension HD ropes [lbs] test', color='g')
    for tl in ax1.get_yticklabels():
        tl.set_color('g')

    ax2 = ax1.twinx()
    ax2.plot_date([mdates.date2num(t[0]) for t in historical_tension],
                  [t[2] for t in historical_tension], 'b-', lw=2, label="Tension HU ropes")
    ax2.set_ylabel('Tension HU ropes [lbs]', color='b')
    for tl in ax2.get_yticklabels():
        tl.set_color('b')
    # format the ticks
    ax2.xaxis.set_minor_locator(mdates.MonthLocator())
    ax2.xaxis.set_minor_formatter(mdates.DateFormatter('%d%b%Y'))
    years= mdates.YearLocator() # every year
    yearsFmt = mdates.DateFormatter('%Y')
    ax2.xaxis.set_major_locator(years)
    ax2.xaxis.set_major_formatter(yearsFmt)

    fig.autofmt_xdate()
    fig = plt.gcf()
    fig.set_size_inches(width / output_dpi, height / output_dpi)
    plt.savefig(output_filename, dpi=output_dpi)
    plt.close()
