'''Extract debugdb views into files.'''

import json
import pprint

with open('debugdb.json') as f:
    doc = json.loads(f.read())

for name, code in doc['views'].items():
    code = json.dumps(code, indent=4)

    code = code.replace('\\n', '\n')

    with open('debugdb/' + name + '.json', 'w') as f:
        f.write(code)

