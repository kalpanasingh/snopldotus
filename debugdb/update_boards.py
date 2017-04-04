'''Update channel info for boards.

This changes channel fields in board documents from lists of bools to richer
structures with status, an array of per-channel tags, and other board type-
specific things (like DC offsets).

Part of migration from old kanso-era debugdb to new Django-fied version.
'''

import couchdb

couch = couchdb.Server('http://couch.snopl.us')
couch.resource.credentials = ('snoplus', 'PureTe->Dirac!=True')
db = couch['debugdb']

do_db = True
do_pmtic = True
do_ctc = True
do_mtca = True
do_xl3 = True
do_mtcd = True
do_caen = True

for row in db.view('debugdb/boards'):
    doc = db[row.id]

    if doc['board_type'] == 'Daughterboard':
        if not do_db:
            continue

        channels = doc.get('channels', [])
        if not 'good' in channels[0]:
            continue

        new_channels = []
        for channel in channels:
            new_channels.append({'ok': channel['good'], 'tags': []})
        doc['channels'] = new_channels
        db.save(doc)

    elif doc['board_type'] == 'PMTIC':
        if not do_pmtic:
            continue

        channels = doc.get('channels', [])
        new_channels = []
        for channel in channels:
            if isinstance(channel, bool):
                new_channels.append({'ok': channel, 'tags': []})
            else:
                new_channels.append(channel)
        doc['channels'] = new_channels

        relays = doc.get('relays', [])
        new_relays = []
        for relay in relays:
            if isinstance(relay, bool):
                new_relays.append({'ok': relay, 'tags': []})
            else:
                new_relays.append(relay)
        doc['relays'] = new_relays

        db.save(doc)

    elif doc['board_type'] == 'CTC':
        if not do_ctc:
            continue

        if 'channels' in doc and isinstance(doc['channels'], list):
            continue

        channels = []
        offsets = doc.get('offsets', {
            "owlelo": 0,
            "esumhi": 0,
            "owlehi": 0,
            "nhit100": 0,
            "owlnhit": 0,
            "esumlo": 0,
            "nhit20": 0
        })

        for k in ['nhit100', 'nhit20', 'esumlo', 'esumhi', 'owlelo', 'owlehi', 'owlnhit']:
            channels.append({'name': k, 'ok': True, 'offset': offsets[k], 'tags': []})

        if 'offsets' in doc:
            del doc['offsets']
        doc['channels'] = channels
        db.save(doc)

    elif doc['board_type'] == 'Front-End Card':
        continue

    elif doc['board_type'] == 'MTC/A+':
        if not do_mtca:
            continue

        if 'channels' in doc:
            continue

        channels = [{'ok': True, 'tags': []} for i in range(20)]

        doc['channels'] = channels

        db.save(doc)

    elif doc['board_type'] == 'XL3':
        if not do_xl3:
            continue

        doc['ml403_ok'] = doc.get('ml403_ok', True)
        doc['sc_reset_ok'] = doc.get('sc_reset_ok', True)

        db.save(doc)

    else:
        print 'Unhandled board:', doc['board_type'], row.id

if do_mtcd and not 'mtcd0' in db:
    print 'Adding mtcd0'
    doc = {
        '_id': 'mtcd0',
        'board_type': 'MTC/D',
        'comments': '',
        'location': 'underground',
        'location_detail': 'timing rack',
        'status': 'gold',
        'type': 'board'
    }
    db.save(doc)

if do_caen and not 'caen0' in db:
    print 'Adding caen0'
    doc = {
        '_id': 'caen0',
        'board_type': 'CAEN v1720',
        'channels': [{'ok': True, 'tags': [], 'input': ''} for i in range(8)],
        'comments': '',
        'location': 'underground',
        'location_detail': 'timing rack',
        'status': 'gold',
        'type': 'board'
    }
    db.save(doc)

