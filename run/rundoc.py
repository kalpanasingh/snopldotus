'''Build a run document from various sources.'''

from django.conf import settings

import json
import httplib
import math
import struct
import numpy as np

def GET(server, path, headers={}):
    '''Replace this with requests.'''
    conn = httplib.HTTPConnection(server)
    conn.request('GET', path, headers=headers)
    response = conn.getresponse()
    return response.read()


def make_headers(content_type='application/json', auth=None):
    h = {
        'Content-type': content_type,
    }
    if auth is not None:
        h['Authorization'] = 'Basic %s' % auth.encode('base64').strip()
    return h


def copy_underscores(doc):
    '''Duplicate keys starting with '_' since you can't use them in Django
    templates.'''
    for k, v in doc.items():
        if k.startswith('_'):
            doc[k.lstrip('_')] = v
    return doc


def unpack_int_array(a):
    size = len(a) / 4
    return struct.unpack('<' + str(size) + 'i', a)


def unpack_double_array(a):
    size = len(a) / 8
    return struct.unpack('<' + str(size) + 'd', a)


def ratdb_load(name, index, run):
    headers = make_headers(auth=settings.ORCADB_AUTH)
    url = '/ratdb-20140407/_design/ratdb/_view/select?include_docs=true&descending=true&limit=1&startkey=["%s","%s",%s]&endkey=["%s","%s"]' % (name, index, run, name, index)
    try:
        data = json.loads(GET(settings.ORCADB_SERVER, url, headers))
        rows = data['rows']
    except Exception:
        return None

    doc = rows[0]['doc']

    if '_attachments' in doc:
        attachments = doc['_attachments']
    else:
        attachments = {}

    for fieldname, info in attachments.items():
        url = '/ratdb-20140407/%s/%s' % (doc['_id'], fieldname)
        try:
            data = GET(settings.ORCADB_SERVER, url, headers)
        except Exception:
            continue
        if info['content_type'] == 'vnd.rat/array-int':
            doc[fieldname] = unpack_int_array(data)
        elif info['content_type'] == 'vnd.rat/array-double':
            doc[fieldname] = unpack_double_array(data)

    return doc


class RunDocument(dict):
    '''All about a run.

    :param number: The unique run ID
    '''
    def __init__(self, number):
        self['number'] = number
        self['orca'] = RunDocument.get_orca(number)
        self['shift'] = RunDocument.get_shift_report(number)
        self['data'] = RunDocument.get_data_flow(number)
        self['processing'] = RunDocument.get_data_processing(number)
        self['calibration'] = RunDocument.get_calibration(number)
        self['quality'] = RunDocument.get_data_quality(number)
        
    @staticmethod
    def get_orca(number):
        '''Load Orca run info from the DB.'''
        headers = make_headers(auth=settings.ORCADB_AUTH)
        url = '/orca/_design/snopldotus/_view/index?include_docs=true&descending=true&startkey=%s&endkey=%s' % (number, number)
        try:
            data = json.loads(GET(settings.ORCADB_SERVER, url, headers))
        except Exception:
            return None

        docs = [x['doc'] for x in data['rows']]

        if len(docs) == 0:
            return None

        doc = docs[0]

        if len(docs) > 1:
            doc['warnings'] = \
              ['Multiple (%i) run documents exist for this run ID.' % len(docs)]

        url = '/orca/_design/snopldotus/_view/config?descending=true&startkey=%s&endkey=%s' % (number, number)
        try:
            config = json.loads(GET(settings.ORCADB_SERVER, url, headers))
        except Exception:
            config = None

        doc['config_id'] = config['rows'][0]['value']

        doc = copy_underscores(doc)

        return doc

    @staticmethod
    def get_shift_report(number):
        '''Load basic shift report information from the Philadelphia DB.'''
        # Get the basic info from the 'runs' view
        headers = make_headers(auth=settings.PHILA_AUTH)
        url = '/phila/_design/phila/_view/runs?descending=true&startkey=%s&endkey=%s&include_docs=true' % (number, number)
        try:
            data = json.loads(GET(settings.PHILA_SERVER, url, headers))
            print data
            docs = [x['doc'] for x in data['rows']]
        except Exception:
            return None

        if len(docs) == 0:
            return None

        doc = docs[0]
        doc = copy_underscores(doc)

        if len(docs) > 1:
            doc['warnings'] = \
              ['Multiple (%i) reports exist for this run ID.' % len(docs)]

        # For convenience, also provide the field list as a dict
        field_dict = {}
        for field in doc['fields']:
            field['value'] = field.get('value', '').replace('\r', '<br/>')
            field_dict[field['name']] = field
        doc['field_dict'] = field_dict

        # Grab comments from the report document
        url = '/phila/%s' % doc['report_id']
        try:
            data = json.loads(GET(settings.PHILA_SERVER, url, headers))
            doc['comments'] = data.get('comments', [])
        except Exception:
            doc['comments'] = None

        return doc

    @staticmethod
    def get_data_flow(number):
        '''Load the data flow information from the DB.'''

        def get_data_rows(filetype):
            headers = make_headers(auth=settings.ORCADB_AUTH)
            url = '/data-processing/_design/dflow/_view/grid_ids?startkey=["%s",%s]&endkey=["%s",%s,{}]' % \
                  (filetype, number, filetype, number)
            try:
                data = json.loads(GET(settings.ORCADB_SERVER, url, headers))
                return data['rows']
            except Exception:
                return []
    
        doc = {'l1_files': get_data_rows("L1"),
               'l2_files': get_data_rows("L2")}
        return doc

    @staticmethod
    def get_data_processing(number):
        '''Load the data processing information from the DB.'''

        headers = make_headers(auth=settings.ORCADB_AUTH)
        url = '/data-processing/_design/dproc/_view/jobs_by_run?key=%s' % (number)
        try:
            data = json.loads(GET(settings.ORCADB_SERVER, url, headers))
            rows = data['rows']
        except Exception:
            return None

        # Add a label field
        labels = {'completed': 'label-success',
                  'failed': 'label-danger',
                  'submitted': 'label-primary',
                  'running': 'label-primary'}
        for row in rows:
            try:
                row['label'] = labels[row['value'][1]]
            except KeyError:
                row['label'] = 'label-default'

        doc = {'jobs': rows}
        return doc

    @staticmethod
    def get_calibration(number):
        '''Get the calibration document (currently PMTCALIB).'''
        doc = ratdb_load('PMTCALIB', '', number)

        def dipolya(Q, hhp):
            m1 = 8.1497;
            gmratio = m1 / np.exp(math.lgamma(m1));
            ng1 = 0.2735E-01;
            ng2 = 0.7944E-03;
            nexp = 0.81228E-01;
            iQ0 = 1 / 20.116;
            G1 = 1.2525 + 0.71726 * hhp;
            G2 = 118.21 + 0.71428 * hhp;
            Qpe1 = Q / G1;
            Qpe2 = Q / G2;
            funpol1 = np.power(m1 * Qpe1, m1 - 1) * np.exp(-m1 * Qpe1);
            funpol2 = np.power(m1 * Qpe2, m1 - 1)* np.exp(-m1 * Qpe2);
            return gmratio * (ng1 * funpol1 + ng2 * funpol2) + nexp * np.exp(-Q * iQ0);

        try:
            x = np.arange(0, 5, 0.1)
            y = dipolya(x, doc['mean_hhp'])
    
            doc['mean_hhp_plot_x'] = x
            doc['mean_hhp_plot_y'] = y
        except Exception:
            doc = {}

        return doc

    @staticmethod
    def get_data_quality(number):
        '''Get the data quality information for the run.'''
        headers = make_headers(auth=settings.DQDB_AUTH)
        url = '/data-quality/_design/data-quality/_view/runs?startkey=%s&endkey=%s&include_docs=true' % (number, number)
        try:
            data = json.loads(GET(settings.DQDB_SERVER, url, headers))
            docs = [x['doc'] for x in data['rows']]
        except Exception:
            raise

        if len(docs) == 0:
            return None

        doc = {}
        doc['doc'] = docs[0]
        return doc
