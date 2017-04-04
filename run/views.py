from django.http import HttpResponse
from django.template import RequestContext, Context, loader
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import condition
from django.conf import settings
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

import json
import datetime
import httplib
import hashlib

import pytz
import dateutil.parser

from run import rundoc

tz = pytz.timezone(settings.PHILA_TZ)
fmt = '%Y/%m/%d %H:%M:%S (%Z)'

ORCA_RUN_TYPES = [
    'Maintenance',
    'Transition',
    'Physics',
    'Deployed Source',
    'External Source',
    'ECA',
    'Diagnostic',
    'Experimental',
    'Supernova',
    'Bit 9 Spare',
    'Bit 10 Spare',
    'Tellie',
    'Smellie',
    'Amellie',
    'PCA',
    'ECA Pedestal',
    'ECA Tslope',
    'Bit 17 Spare',
    'Bit 18 Spare',
    'Bit 19 Spare',
    'Bit 20 Spare',
    'DCR Activity',
    'Comp. Coils OFF',
    'PMTs OFF',
    'Bubblers',
    'Recirculation',
    'Slassay',
    'Unusual Activity',
    'Bit 28 Spare',
    'Bit 29 Spare',
    'Bit 30 Spare',
    'Bit 31 Spare',
]

@login_required
def index(request):
    '''Run list.'''
    t = loader.get_template('run/index.html')
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    start = int(request.GET.get('start', 0))
    limit = int(request.GET.get('limit', 15))

    headers = rundoc.make_headers(auth=settings.ORCADB_AUTH)
    url = '/orca/_design/snopldotus/_view/index?include_docs=true&descending=true&skip=%i&limit=%i' % (start, limit)
    data = json.loads(rundoc.GET(settings.ORCADB_SERVER, url, headers))

    total_runs = data['total_rows']
    runs = [x['doc'] for x in data['rows']]

    live_time = datetime.timedelta(0)
    start_time = None
    end_time = None

    for run in runs:
        run['id'] = run['_id']
        run_start = run['run_start'] if 'run_start' in run else run['sudbury_time_start']
        run_stop = run['run_stop'] if 'run_stop' in run else run.get('sudbury_time_end')
        run['run_number'] = run.get('run', run.get('run_number'))

        run_start = dateutil.parser.parse(run_start)
        run['run_start'] = run_start

        start_time = run_start

        if run_stop:
            run_stop = dateutil.parser.parse(run_stop)
            run['run_stop'] = run_stop
            run['duration'] = run_stop - run_start
            live_time += run['duration']

            if end_time is None:
                end_time = run_stop

    if end_time is None:
        end_time = start_time

    total_time = end_time - start_time
    live_fraction = 100.0 * live_time.total_seconds() / total_time.total_seconds()

    c = RequestContext(request, {
        'total_runs': total_runs,
        'runs': runs,
        'live_time': live_time,
        'total_time': total_time,
        'live_fraction': live_fraction,
        'previous_start': max(start - limit, 0),
        'next_start': start + limit,
        'start': start
    })
    return HttpResponse(t.render(c))


@login_required
def run(request, run_id):
    '''View details for a particular run.'''
    t = loader.get_template('run/run.html')
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    run_id = int(run_id)
    doc = rundoc.RunDocument(run_id)
    doc['index_start'] = int(request.GET.get('index_start', 0))

    # Localize timestamps
    run_start = doc['orca']['run_start'] if 'run_start' in doc['orca'] else doc['orca']['sudbury_time_start']
    run_stop = doc['orca']['run_stop'] if 'run_stop' in doc['orca'] else doc['orca'].get('sudbury_time_end')

    doc['orca']['run_start'] = dateutil.parser.parse(run_start)
    doc['orca']['run_stop'] = dateutil.parser.parse(run_stop)

    # Run type formatting
    run_type_word = doc['orca'].get('run_type', 0)
    run_types = []
    for bit in range(len(ORCA_RUN_TYPES)):
        if run_type_word & (1 << bit):
            run_types.append(ORCA_RUN_TYPES[bit])
    doc['orca']['run_type'] = ', '.join(run_types) + ' (%i)' % run_type_word

    c = RequestContext(request, doc)
    return HttpResponse(t.render(c))

