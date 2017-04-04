'''Push debugdb views to a CouchDB server.

debugdb views are stored in the debugdb subdirectory for editing.
'''

import json
import glob
import os
import pprint
import re
import sys
import requests

if len(sys.argv) != 2:
    print 'Usage:', sys.argv[0], 'http://myserver.com:5984/debugdb'

server = sys.argv[1]
headers = {
    'content-type': 'application/json',
    'referer': 'http://localhost:5984'
}
docs = []

# Views for penn_daq and whatnot
for view in ['crate_init_views', 'penn_daq_views']:
    with open (view + '.json') as f:
        v = json.load(f)

    try:
        r = requests.get(server + '/_design/' + view)
        v['_rev'] = r.json()['_rev']
    except Exception:
        pass

    docs.append(v)

# View loaded from debugdb directory
views = {}
for filename in glob.glob('debugdb/*.json'):
    name = os.path.basename(filename).split('.')[0]
    with open(filename) as f:
        pattern = re.compile(r'".*?"', re.DOTALL)
        data = pattern.sub(lambda x: x.group().replace('\n', '\\n'), f.read())
        views[name] = json.loads(data)

doc = {
    '_id': '_design/debugdb',
    'language': 'javascript',
    'views': views
}

try:
    r = requests.get(server + '/_design/debugdb')
    doc['_rev'] = r.json()['_rev']
except Exception:
    pass

docs.append(doc)

data = json.dumps({'docs': docs})

r = requests.post(server + '/_bulk_docs', data=data, headers=headers)
pprint.pprint(r.json())

