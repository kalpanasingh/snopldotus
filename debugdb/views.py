from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.contrib.auth.decorators import login_required
from django.conf import settings

import requests
import json
import datetime
import hashlib
import dateutil.parser
import dateutil.tz

# Set up headers used for all requests to the debugdb CouchDB database
headers = {
    'Content-type': 'application/json',
}

if settings.DEBUGDB_AUTH is not None:
    headers['Authorization'] = 'Basic %s' % settings.DEBUGDB_AUTH.encode('base64')[:-1]


def get_stats():
    '''Get the board statistics (what's where, statuses).'''
    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/board_stats',
                     params={'group_level': 1},
                     headers=headers)
    boards = {x['key']: x['value'] for x in r.json()['rows']}

    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/fec_stats',
                     params={'group_level': 1},
                     headers=headers)
    fecs = {x['key']: x['value'] for x in r.json()['rows']}

    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/db_stats',
                     params={'group_level': 1},
                     headers=headers)
    dbs = {x['key']: x['value'] for x in r.json()['rows']}

    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/location_stats',
                     params={'group_level': 1},
                     headers=headers)
    locs = {x['key']: x['value'] for x in r.json()['rows']}

    return {
        'boards': boards,
        'fecs': fecs,
        'dbs': dbs,
        'locations': locs,
    }


def find_location(board_id, config):
    '''Locate a board in the configuration.'''
    if board_id[0] == 'f':
        for i, crate in enumerate(config['crates']):
            for j, fec in enumerate(crate['fecs']):
                if fec['id'] == board_id:
                    return {'csd': (i, j)}

    elif board_id[0] == 'e':
        for i, crate in enumerate(config['crates']):
            for j, pmtic in enumerate(crate['pmtics']):
                if pmtic == board_id:
                    return {'csd': (i, j)}

    elif board_id[0] == 'd':
        for i, crate in enumerate(config['crates']):
            for j, fec in enumerate(crate['fecs']):
                for k, db in enumerate(fec['dbs']):
                    if db == board_id:
                        return {'csd': (i, j, k)}

    elif board_id.startswith('c0'):
        for i, crate in enumerate(config['crates']):
            if crate['ctc'] == board_id:
                return {'csd': (i,)}

    elif board_id.startswith('x'):
        for i, crate in enumerate(config['crates']):
            if crate['xl3'] == board_id:
                return {'csd': (i,)}

    elif board_id[0] == 't':
        for i, mtca in enumerate(config['timing_rack']['mtca']):
            if mtca == board_id:
                return {'timing': ('MTC/A+', i)}

    elif board_id.startswith('mtcd'):
        if config['timing_rack']['mtcd'] == board_id:
            return {'timing': ('VME',)}

    elif board_id.startswith('caen'):
        if config['timing_rack']['caen'] == board_id:
            return {'timing': ('VME',)}

    return None
        

@login_required
def index(request):
    '''debugdb home page.'''
    t = loader.get_template('debugdb/index.html')
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/tests_by_created',
                     params={'limit': 10},
                     headers=headers)

    c = RequestContext(request, {
      'tests': r.json()['rows'],
      'stats': get_stats()
    })
    return HttpResponse(t.render(c))


@login_required
def boards(request):
    '''Board list.'''
    t = loader.get_template('debugdb/boards.html')
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/boards',
                     headers=headers)

    c = RequestContext(request, {
        'boards': r.json()['rows'],
    })
    return HttpResponse(t.render(c))


@login_required
def board(request, board_id):
    '''Board details.

    POST updates the board metadata, others show the board page.
    '''
    if request.method == 'POST':
        # Get the board document
        r = requests.get(settings.DEBUGDB_SERVER + '/debugdb/' + board_id,
                         headers=headers)
        board = r.json()

        form_data = {k: request.POST[k] for k in request.POST}
        del form_data['csrfmiddlewaretoken']

        for field in ['status', 'location', 'location_detail', 'comments']:
            board[field] = form_data.get(field, '')

        for i, channel in enumerate(board.get('channels', [])):
            channel['ok'] = True if '%s-%s-%i' % (board_id, 'channels', i) in form_data else False

            if 'offset' in channel:
                channel['offset'] = form_data.get('offset-%i' % i, '')

            if 'input' in channel:
                channel['input'] = form_data.get('input-source-%i' % i, '')

        for i, channel in enumerate(board.get('relays', [])):
            channel['ok'] = True if '%s-%s-%i' % (board_id, 'relays', i) in form_data else False

        r = requests.put(settings.DEBUGDB_SERVER +
                         '/debugdb/' + board_id,
                         data=json.dumps(board),
                         headers=headers)

        return HttpResponseRedirect('/debugdb/board/' + board_id)

    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    # Board document
    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/%s' % board_id,
                     headers=headers)
    board = r.json()
    board['id'] = board['_id']

    if board['board_type'] == 'CTC':
        t = loader.get_template('debugdb/boards/ctc.html')
    elif board['board_type'] == 'Daughterboard':
        t = loader.get_template('debugdb/boards/daughterboard.html')
    elif board['board_type'] == 'Front-End Card':
        t = loader.get_template('debugdb/boards/fec.html')
    elif board['board_type'] == 'XL3':
        t = loader.get_template('debugdb/boards/xl3.html')
    elif board['board_type'] == 'PMTIC':
        t = loader.get_template('debugdb/boards/pmtic.html')
    elif board['board_type'] == 'MTC/A+':
        t = loader.get_template('debugdb/boards/mtca.html')
    elif board['board_type'] == 'MTC/D':
        t = loader.get_template('debugdb/boards/mtcd.html')
    elif board['board_type'] == 'CAEN v1720':
        t = loader.get_template('debugdb/boards/caen_v1720.html')
    else:
        t = loader.get_template('debugdb/boards/unknown.html')

    # Debugging status tags
    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/tags_by_board',
                     params={'startkey': '["%s"]' % board_id, 'endkey': '["%s", {}]' % board_id},
                     headers=headers)
    tags = r.json()
    board['tags'] = tags['rows']

    # Configuration
    r = requests.get(settings.DEBUGDB_SERVER + '/debugdb/configuration_snoplus',
                     headers=headers)
    config = r.json()

    board['ccc_location'] = find_location(board_id, config)

    # Tests
    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/tests_by_id',
                     params={'limit': 10, 'startkey': '["%s"]' % board_id, 'endkey': '["%s", {}]' % board_id},
                     headers=headers)
    tests = r.json()
    board['tests'] = tests['rows']

    # ECALs?

    # FEC documents
    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/get_fec_by_board_id',
                     params={'descending': 'true', 'endkey': '["%s"]' % board_id, 'startkey': '["%s", {}]' % board_id},
                     headers=headers)
    fecdocs = r.json()
    board['fecdocs'] = fecdocs['rows']
    c = RequestContext(request, board)

    return HttpResponse(t.render(c))


@login_required
def test(request, test_id):
    '''Test results.'''
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    # Test document
    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/%s' % test_id,
                     headers=headers)
    test = r.json()
    test['id'] = test['_id']

    if test['type'] == 'final_test':
        r = requests.get(settings.DEBUGDB_SERVER +
                         '/debugdb/_design/debugdb/_view/final_test',
                         params={'startkey': '["%s"]' % test_id, 'endkey': '["%s", {}]' % test_id},
                         headers=headers)
        tests = r.json()['rows'][1:]

        # Sort sub-tests by creation time
        date_ts = lambda x: dateutil.parser.parse(x).strftime("%s")
        test['tests'] = sorted(tests, key=lambda x: date_ts(x['value']['created']))

        # One test (the pre-balance ped_run) is allowed to fail; this is lazy
        passed = len(filter(lambda x: x['value']['pass'], tests))
        test['pass'] = (passed >= len(tests) - 1)

    if test['type'] == 'ecal':
        for crate in test['crates']:
            slots = [None for i in range(16)]
            for slot in crate['slots']:
                slots[slot['slot_id']] = slot
            crate['slots'] = slots

        r = requests.json(settings.DEBUGDB_SERVER +
                         '/debugdb/_design/debugdb/_view/ecal',
                         params={'startkey': '["%s"]' % test_id, 'endkey': '["%s", {}]' % test_id},
                         headers=headers)
        rows = r.json()['rows'][1:]

        tests = {crate['crate_id']: {} for crate in test['crates']}

        for row in rows:
            if 'type' not in row['value'] or row['value']['type'] == 'FEC':
                continue
            crate = row['value']['config']['crate_id']
            slot = row['value']['config']['slot']
            row['value']['id'] = row['value']['_id']

            if slot in tests[crate]:
                tests[crate][slot].append(row['value'])
            else:
                tests[crate][slot] = [row['value']]

        test['tests'] = tests

    t = loader.get_template('debugdb/tests/%s.html' % test['type'])
    c = RequestContext(request, test)

    return HttpResponse(t.render(c))


@login_required
def test_names(request):
    '''A list of test names.'''
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/tests',
                     params={'group': 'true'},
                     headers=headers)

    data = r.json()
    names = data['rows']

    t = loader.get_template('debugdb/test_names.html')
    c = RequestContext(request, {'tests': names})

    return HttpResponse(t.render(c))


@login_required
def tests(request, name=None, board_id=None):
    '''A list of all tests.'''
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    start = int(request.GET.get('start', 0))
    limit = int(request.GET.get('limit', 15))

    if name:
        r = requests.get(settings.DEBUGDB_SERVER +
                         '/debugdb/_design/debugdb/_view/tests_by_name',
                         params={'startkey': '["%s"]' % name, 'endkey': '["%s",{}]' % name, 'skip': start, 'limit': limit},
                         headers=headers)

    elif board_id:
        r = requests.get(settings.DEBUGDB_SERVER +
                         '/debugdb/_design/debugdb/_view/tests_by_id',
                         params={'startkey': '["%s"]' % board_id, 'endkey': '["%s",{}]' % board_id, 'skip': start, 'limit': limit},
                         headers=headers)

    else:
        r = requests.get(settings.DEBUGDB_SERVER +
                         '/debugdb/_design/debugdb/_view/tests_by_created',
                         params={'skip': start, 'limit': limit},
                         headers=headers)

    data = r.json()
    tests = data['rows']
    total_rows = data['total_rows']

    t = loader.get_template('debugdb/tests.html')
    c = RequestContext(request, {
        'name': name,
        'board_id': board_id,
        'start': start,
        'limit': limit,
        'tests': tests,
        'total_rows': total_rows
    })

    return HttpResponse(t.render(c))


@login_required
def crate(request, crate_id):
    '''Overview of a crate.'''
    def get_board(board_id):
        try:
            r = requests.get(settings.DEBUGDB_SERVER + '/debugdb/' + board_id,
                             headers=headers)
            doc = r.json()
            doc['id'] = doc['_id']
        except Exception:
            doc = None
        return doc

    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    crate_id = int(crate_id)

    # Get all statuses
    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/tags_with_status',
                     params={'group_level': 1},
                     headers=headers)
    rows = r.json()['rows']
    statuses = {x['key']: x['value'][1] for x in rows}

    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/configuration_snoplus',
                     headers=headers)
    config_doc = r.json()['crates'][crate_id]

    xl3_doc = get_board(config_doc['xl3'])
    ctc_doc = get_board(config_doc['ctc'])

    config = {
        'crate_id': crate_id,
        'xl3': xl3_doc,
        'ctc': ctc_doc,
        'slots': [],
        'statuses': statuses,
    }

    for fec, pmtic in zip(*(config_doc['fecs'], config_doc['pmtics'])):
        try:
            fec_doc = get_board(fec['id'])
        except Exception:
            raise Exception(fec)
        pmtic_doc = get_board(pmtic)

        dbs = []
        for db in fec['dbs']:
            db_doc = get_board(db)
            dbs.append(db_doc)

        config['slots'].append({
            'fec': fec_doc,
            'pmtic': pmtic_doc,
            'dbs': dbs,
        })

    t = loader.get_template('debugdb/crate.html')
    c = RequestContext(request, config)

    return HttpResponse(t.render(c))


@login_required
def ecals(request):
    '''List of all ECALs.'''
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    start = int(request.GET.get('start', 0))
    limit = int(request.GET.get('limit', 15))

    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/ecals_by_created',
                     params={'skip': start, 'limit': limit},
                     headers=headers)

    data = r.json()
    ecals = data['rows']
    total_rows = data['total_rows']

    t = loader.get_template('debugdb/ecals.html')
    c = RequestContext(request, {
        'start': start,
        'limit': limit,
        'ecals': ecals,
        'total_rows': total_rows
    })

    return HttpResponse(t.render(c))


@login_required
def ecal(request, test_id):
    '''Results of an ECAL.'''
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    # ECAL document
    r = requests.get(settings.DEBUGDB_SERVER + '/debugdb/' + test_id,
                     headers=headers)
    test = r.json()
    test['id'] = test['_id']

    for crate in test['crates']:
        slots = [None for i in range(16)]
        for slot in crate['slots']:
            slots[slot['slot_id']] = slot
        crate['slots'] = slots

    # Config document
    r = requests.get(settings.DEBUGDB_SERVER + '/debugdb/configuration_snoplus',
                     headers=headers)
    test['configuration'] = r.json()

    # Test sub-documents
    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/ecal',
                     params={'startkey': '["%s"]' % test_id, 'endkey': '["%s",{}]' % test_id},
                     headers=headers)
    rows = r.json()['rows'][1:]

    tests = {crate['crate_id']: {} for crate in test['crates']}

    for row in rows:
        if 'type' not in row['value'] or row['value']['type'] == 'FEC':
            continue
        crate = row['value']['config']['crate_id']
        slot = row['value']['config']['slot']
        row['value']['id'] = row['value']['_id']

        if slot in tests[crate]:
            tests[crate][slot].append(row['value'])
        else:
            tests[crate][slot] = [row['value']]

    test['tests'] = tests

    t = loader.get_template('debugdb/ecal.html')
    c = RequestContext(request, test)

    return HttpResponse(t.render(c))


@login_required
def spares(request):
    '''List of spare boards, i.e. what is not in the detector.'''
    t = loader.get_template('debugdb/spares.html')
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    # Make a list of boards in the detector
    r = requests.get(settings.DEBUGDB_SERVER + '/debugdb/configuration_snoplus',
                     headers=headers)
    config = r.json()

    used_boards = []
    for crate in config['crates']:
        used_boards.append(crate['ctc'])
        used_boards.append(crate['xl3'])
        for pmtic in crate['pmtics']:
            used_boards.append(pmtic)
        for fec in crate['fecs']:
            used_boards.append(fec['id'])
            for db in fec['dbs']:
                used_boards.append(db)

    timing = config['timing_rack']
    used_boards.append(timing['mtcd'])
    used_boards.append(timing['caen'])
    for mtca in timing['mtca']:
        used_boards.append(mtca)

    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/boards',
                     headers=headers)
    boards = r.json()['rows']

    spares = {x: [] for x in ['Front-End Cards', 'Daughterboards', 'CTCs', 'PMTICs', 'XL3s', 'MTC/A+s', 'Others']}

    for board in boards:
        if board['id'] in used_boards:
            continue

        b = {
            'id': board['id'],
            'status': board['value'][0],
            'location': board['value'][1],
        }

        if board['id'][:1] == 'f':
            spares['Front-End Cards'].append(b)
        elif board['id'][:1] == 'd':
            spares['Daughterboards'].append(b)
        elif board['id'][:2] == 'c0':
            spares['CTCs'].append(b)
        elif board['id'][:1] == 'e':
            spares['PMTICs'].append(b)
        elif board['id'][:1] == 'x':
            spares['XL3s'].append(b)
        elif board['id'][:1] == 't':
            spares['MTC/A+s'].append(b)
        else:
            spares['Others'].append(b)

    c = RequestContext(request, {
        'spares': spares,
    })
    return HttpResponse(t.render(c))


@login_required
def detector(request, crate_id=2):
    '''Overview of the entire detector.'''
    def get_board(board_id):
        r = requests.get(settings.DEBUGDB_SERVER + '/debugdb/' + board_id,
                         headers=headers)
        doc = r.json()
        doc['id'] = doc['_id']

        r = requests.get(settings.DEBUGDB_SERVER,
                         '/debugdb/_design/debugdb/_view/tags_with_status',
                         params={'group_level': 1, 'key': '"%s"' % board_id},
                         headers=headers)

        try:
            tag = r.json()['rows'][0]
            status = tag['value'][1]
        except Exception:
            status = 'notags'

        return doc, status

    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    # Get the status of every board
    r = requests.get(settings.DEBUGDB_SERVER +
                     '/debugdb/_design/debugdb/_view/boards',
                     headers=headers)
    boards = r.json()['rows']
    statuses = {}
    for row in boards:
        statuses[row['id']] = row['value'][0]

    # Get the config doc
    r = requests.get(settings.DEBUGDB_SERVER + '/debugdb/configuration_snoplus',
                     headers=headers)
    config_doc = r.json()

    config_doc['statuses'] = statuses

    t = loader.get_template('debugdb/detector.html')
    c = RequestContext(request, config_doc)

    return HttpResponse(t.render(c))


@login_required
def new_tag(request):
    '''Create a new tag.

    This may be either a board tag (i.e. a new tag document) or a channel
    tag, which are in the channels array inside a board document. We assume
    it's the latter if 'field', which is the name of the key ("channels",
    "relays", etc.), is in the POST request.
    '''
    if request.method == 'POST':
        board_id = request.POST.get('board')

        # Board tag: create a new tag document
        if not 'field' in request.POST:
            doc = {
               "type": "tag",
               "created": datetime.datetime.now(dateutil.tz.tzlocal()).strftime('%a %b %d %Y %T GMT%z (%Z)'),
               "author": request.POST.get('author', ''),
               "board": request.POST.get('board', ''),
               "status": request.POST.get('status', 'none'),
               "content": request.POST.get('content', '')
            }
            r = requests.post(settings.DEBUGDB_SERVER + '/debugdb/',
                              data=json.dumps(doc),
                              headers=headers)

        # Channel tag: update the board document
        else:
            r = requests.get(settings.DEBUGDB_SERVER + '/debugdb/' + board_id,
                             headers=headers)
            board = r.json()

            doc = {
               "created": datetime.datetime.now(dateutil.tz.tzlocal()).strftime('%a %b %d %Y %T GMT%z (%Z)'),
               "author": request.POST.get('author', ''),
               "status": request.POST.get('status', 'none'),
               "content": request.POST.get('content', '')
            }

            board[request.POST['field']][int(request.POST['index'])]['tags'].append(doc)

            r = requests.put(settings.DEBUGDB_SERVER + '/debugdb/' + board_id,
                             data=json.dumps(board),
                             headers=headers)

        # Redirect back to the board's page
        # It would be good to do something nicer if the post/put fails
        return HttpResponseRedirect('/debugdb/board/' + board_id)


@login_required
def fecdoc(request, doc_id):
    '''View a FEC document.'''
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    # FEC document
    r = requests.get(settings.DEBUGDB_SERVER + '/debugdb/' + doc_id,
                     headers=headers)
    doc = r.json()
    doc['ids'] = doc['id']
    doc['id'] = doc['_id']

    # Test results
    for k, v in doc['test'].items():
        r = requests.get(settings.DEBUGDB_SERVER + '/debugdb/' + v['test_id'],
                         headers=headers)
        doc['test'][k]['pass'] = r.json()['pass']

    t = loader.get_template('debugdb/fec_document.html')
    c = RequestContext(request, doc)

    return HttpResponse(t.render(c))

@login_required
def reconfig(request):
    '''Swap a board in the configuration document.'''
    if request.method == 'POST':
        crate_id = request.POST.get('crate')
        slot_id = request.POST.get('slot')
        db_id = request.POST.get('db')
        current = request.POST.get('board')
        new = request.POST.get('new-board')
        board_type = request.POST.get('type')

        if current:
            assert(new[0] == current[0])

        # Configuration document
        r = requests.get(settings.DEBUGDB_SERVER + '/debugdb/configuration_snoplus',
                         headers=headers)
        config = r.json()

        # Remove old board from existing location
        if new.startswith('c0'):
            for i, crate in enumerate(config['crates']):
                if crate['ctc'] == new:
                    config['crates'][i]['ctc'] = None
                    break
        elif new.startswith('x'):
            for i, crate in enumerate(config['crates']):
                if crate['xl3'] == new:
                    config['crates'][i]['xl3'] = None
                    break
        elif new.startswith('f'):
            for i, crate in enumerate(config['crates']):
                for j, fec in enumerate(crate['fecs']):
                    if fec['id'] == new:
                        config['crates'][i]['fecs'][j]['id'] = None
        elif new.startswith('e'):
            for i, crate in enumerate(config['crates']):
                for j, pmtic in enumerate(crate['pmtics']):
                    if pmtic == new:
                        config['crates'][i]['pmtics'][j] = None
        elif new.startswith('d'):
            for i, crate in enumerate(config['crates']):
                for j, fec in enumerate(crate['fecs']):
                    for k, db in enumerate(crate['fecs']):
                        if db == new:
                            config['crates'][i]['fecs'][j]['dbs'][k] = None
                            break
        elif new.startswith('t'):
            for i, mtca in enumerate(config['timing_rack']['mtcd']):
                if mtca == new:
                    config['timing_rack']['mtca'][i] = None
                    break

        # And place it
        if board_type == 'ctc':
            assert(new.startswith('c0'))
            config['crates'][int(crate_id)]['ctc'] = new
        elif board_type == 'xl3':
            assert(new.startswith('x'))
            config['crates'][int(crate_id)]['xl3'] = new
        elif board_type == 'fec':
            assert(new.startswith('f'))
            config['crates'][int(crate_id)]['fecs'][int(slot_id)]['id'] = new
        elif board_type == 'pmtic':
            assert(new.startswith('e'))
            config['crates'][int(crate_id)]['pmtics'][int(slot_id)] = new
        elif board_type == 'db':
            assert(new.startswith('d'))
            config['crates'][int(crate_id)]['fecs'][int(slot_id)]['dbs'][int(db_id)] = new
        elif board_type == 'mtcd':
            assert(new.startswith('mtcd'))
            config['timing_rack']['mtcd'] = new
        elif board_type == 'caen':
            assert(new.startswith('caen'))
            config['timing_rack']['caen'] = new
        elif board_type == 'mtca':
            assert(new.startswith('t'))
            config['timing_rack']['mtca'][int(slot_id)] = new
        else:
            raise Exception('Error reconfiguring ' + current + ' <- ' + new + ' (' + board_type + ')')

        r = requests.put(settings.DEBUGDB_SERVER + '/debugdb/configuration_snoplus',
                         data=json.dumps(config),
                         headers=headers)

        return HttpResponseRedirect('/debugdb/crate/' + crate_id)

