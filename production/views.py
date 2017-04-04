from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext, Context, loader
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.conf import settings
from django.forms.formsets import formset_factory, BaseFormSet
from wsgiref.util import FileWrapper
from production.forms import BenchmarkingForm, ResultsForm, BaseRequestFormset, MacroFormByTime, MacroFormByNumber

import httplib
import base64
import json
import string
import csv
import copy


_known_subs = ['z', 'day', 'rate', 'radius']


def connect_db():
    '''Connect to the benchmarking database
    '''
    conn = httplib.HTTPConnection(settings.BENCH_SERVER)
    headers = {'Content-type': 'application/json',}
    if settings.BENCH_AUTH is not None:
        authstring = 'Basic {0}'.format(base64.encodestring(settings.BENCH_AUTH)[:-1])
        headers['Authorization'] = authstring
    return conn, headers


def get(url):
    '''return JSON for GET request to the benchmarking database
    '''
    conn, headers = connect_db()
    conn.request('GET', url, headers = headers)
    response = conn.getresponse()
    if not response.status < 400:
        raise Exception('database not found')
    data = json.loads(response.read())
    return data


def post(url, body):
    '''return JSON for GET request to the benchmarking database
    '''
    conn, headers = connect_db()
    conn.request('POST', url, body, headers = headers)
    response = conn.getresponse().read()
    return json.loads(response)

def get_versions_benchmarked():
    '''Get the versions of RATDB that have been used for benchmarking
    '''
    url = '\
/{0}/_design/benchmark/_view/macro_by_version_phase?descending=true&reduce=true&group_level=1'.\
format(settings.BENCH_NAME)
    response = get(url)
    # Rows will have keys, 1st element is the rat version
    return [v['key'][0] for v in response['rows']]

def get_versions_available():
    '''Get the versions of RATDB available for benchmarking
    '''
    url = '\
/{0}/_design/benchmark/_view/rat_versions?descending=true'.\
format(settings.BENCH_NAME)
    response = get(url)
    return [v['key'] for v in response['rows']]

def get_phases(version):
    '''Get the versions of RATDB that have been used for benchmarking
    '''
    url = '\
/{db}/_design/benchmark/_view/macro_by_version_phase?reduce=true&group_level=2&\
startkey=["{v}"]&endkey=["{v}",{{}}]'.\
format(db = settings.BENCH_NAME, v = version)
    response = get(url)
    # Rows will have keys, 2nd element is the descriptor
    return [v['key'][1] for v in response['rows']]

def get_names():
    '''Get the names of users submitting macros
    '''
    url = '\
/{0}/_design/benchmark/_view/macro_by_user?reduce=true&group_level=1'.\
format(settings.BENCH_NAME)
    response = get(url)
    # Keyed only by user name
    return [v['key'] for v in response['rows']]

def get_results(version, phase = None):
    '''Get benchmarking results for a given RAT version
    '''
    if phase is not None:
        key = '"{v}","{p}"'.format(v = version, p = phase)
    else:
        key = '"{v}"'.format(v = version)
    url = '\
/{db}/_design/benchmark/_view/macro_by_version_phase?startkey=[{k}]&endkey=[{k},{{}}]&reduce=false&include_docs=true'.\
format(db = settings.BENCH_NAME, k = key)
    response = get(url)
    # Need to separate out completed from other job types
    results = []
    tags = []
    ids = []
    tag_map = {'completed': 'success',
               'failed': 'danger',
               'running': 'active',
               'waiting': ''}
    for row in response['rows']:
        status = row['doc']['state']
        results.append({'descriptor': row['key'][1],
                        'macro': row['value'],
                        'commit': row['key'][2],
                        'status': status})
        ids.append(row["id"])
        try:
            tags.append(tag_map[status])
        except KeyError:
            tags.append('warning')
        if status == 'completed':
            results[-1]['size'] = row['doc']['eventSize']/1024.0
            results[-1]['time'] = row['doc']['eventTime']['Total']
        else:
            results[-1]['size'] = None
            results[-1]['time'] = None
    return ('Descriptor', 'Macro', 'Commit', 'State', 'Event (kB)', 'Time / event (s)'), results, ids, tags


def get_templates(macro):
    '''Return a list of templated strings.
    '''
    templates = set()
    for (_, t1, t2, _) in string.Template.pattern.findall(macro):
        # 1st element is e.g. $$ (escaped)
        # last element are bad formed
        if t1 != '':
            templates.add(t1)
        elif t2 != '':
            templates.add(t2)
    return list(templates)


@login_required
def benchmarking_request(request):
    '''View for the benchmarking request page.
    '''
    versions = get_versions_available()
    alert = None
    if request.method == 'POST':
        form = BenchmarkingForm(versions, request.POST, request.FILES)
        if form.is_valid():
            # Want to validate any template strings, would involve uploading the file to django,
            # checking it, then uploading on to couchdb.  Potentially a bit involved.
            # Generate a new document, contains an ``info'' dictionary with keys of macro name
            # and values of waiting
            file_list = request.FILES.getlist('attachments')
            document_base = {'requestedBy': request.POST['name'],
                             'descriptor': request.POST['descriptor'],
                             'ratVersion': request.POST['rat_version'],
                             'commitHash': request.POST['commit_hash'],
                             'type': 'macro',
                             'state': 'waiting'}
            documents = [copy.copy(document_base) for f in file_list]

            for i, f in enumerate(file_list):
                documents[i]['name'] = f.name

            data = post('/{0}/_bulk_docs'.format(settings.BENCH_NAME), json.dumps({'docs': documents}))

            # Get the doc IDs (order should be retained!)
            for i, (info, f) in enumerate(zip(data, file_list)):
                macro_contents = f.read()
                templates = get_templates(macro_contents)

                documents[i]['_id'] = info['id']
                documents[i]['_rev'] = info['rev']
                documents[i]['_attachments'] = {f.name: {'content_type': 'text/plain',
                                                         'data': macro_contents.encode('base64')}}
                documents[i]['templates'] = templates
                
            data = post('/{0}/_bulk_docs'.format(settings.BENCH_NAME), json.dumps({'docs': documents}))

            alert = 'Benchmarking request submitted for: '
            if len(file_list) > 5:
                alert += ' %d macros' % len(file_list)
            else:
                alert += ', '.join(f.name for f in file_list)
        # Else Django handles this
    else:
        form = BenchmarkingForm(versions)
        alert = None

    return render(
        request,
        'production/benchmarking/request.html',
        {'form': form,
         'alert': alert})


# Need to know the version from the previous post
_version = None
_phases = None
@login_required
def benchmarking_results(request):
    '''View for the benchmarking results page
    '''
    global _version, _phases
    # First need to get the list of available options from the benchmarking database
    versions = get_versions_benchmarked()
    names = get_names()
    if request.method == 'POST':
        version = request.POST['version']
        phase = request.POST['phase']
        if version != _version:
            # Updated the version, get all results and populate the phase list
            # If the current phase in also available for the updated version, use that
            _phases = get_phases(version)
            if phase in _phases:
                results_headings, results_list, id_list, tag_list = get_results(version, phase)
            else:
                results_headings, results_list, id_list, tag_list = get_results(version)
            _version = version
        else:
            # Updated the phase, get results filtered for this phase
            if phase == 'None':
                phase = None
            results_headings, results_list, id_list, tag_list = get_results(version, phase)
        form = ResultsForm(versions,  _phases, None, request.POST)
    else:
        form = ResultsForm(versions, [], None)
        results_list = []
        tag_list = []
        id_list = []
        results_headings = []
        
    return render(
        request,
        'production/benchmarking/results.html',
        {'form': form,
         'phases': _phases,
         'results_zip': zip(tag_list, results_list, id_list),
         'results_headings': results_headings})


@login_required
def production_request(request):
    '''View to handle requests of production data
    '''
    # Should update to formset with checkboxes so that
    # an error can be displayed if no checkboxes are ticked
    if request.GET['submit'] == "Form-Number" or\
       request.GET['submit'] == "Form-Time":
        return generate_request_form(request)
    else:
        return download_production_request(request)


def generate_request_form(request):
    '''Produce the formset used to generate production request JSON
    '''
    if request.GET['submit'] == "Form-Number":
        page = "production/request-by-number.html"
        baseform = MacroFormByNumber
    else:
        page = "production/request-by-time.html"
        baseform = MacroFormByTime

    # Start by getting macro information again...
    box_values = request.GET.getlist('requestbox')
    ids = set()
    for v in box_values:
        ids.add(v.partition('_')[0])
    # Bulk get from couchdb
    data = post('/{0}/_all_docs?include_docs=true'.format(settings.BENCH_NAME),
                json.dumps({'keys': list(ids)}))
    docs = {}
    for row in data['rows']:
        if row['id'] not in docs:
            docs[row['id']] = row['doc']
    # Get the time and data-size for each macro
    rat_version = None
    macro_info = {}
    for v in box_values:
        doc_id, _, macro = v.partition('_')
        doc = docs[doc_id]
        macro_info[v] = {}
        macro_info[v]['macro'] = macro
        macro_info[v]['phase'] = doc['descriptor']
        macro_info[v]['time'] = doc['eventTime']['Total']
        macro_info[v]['size'] = doc['eventSize'] / 1024.0
        macro_info[v]['templates'] = doc.get('templates', [])
        if 'rate' in macro_info[v]['templates']:
            fixed_rate = False
        else:
            fixed_rate = True
        macro_info[v]['fixed_rate'] = fixed_rate
        if not rat_version:
            rat_version = doc['ratVersion']
        if rat_version != doc['ratVersion']:
            raise ValueError("Mutliple versions of RAT!")

    form_entries = []
    for i, (v, m) in enumerate(sorted(macro_info.iteritems())):
        entry_info = {'phase': m['phase'],
                      'macro': m['macro'],
                      'time': m['time'],
                      'size': m['size'],
                      'fixed_rate': m['fixed_rate'],
                      'templates': m['templates']}
        form_entries.append(entry_info)

    request_formset = formset_factory(baseform, BaseRequestFormset, extra=0)
    formset = request_formset(initial = form_entries)

    return render(
        request,
        page,
        {'formset': formset,
         'rat_version': rat_version})

    

def mangle_module_name(phase, macro):
    '''Convert phase and macro name to production module name
    Note: phase needs to be e.g. solar, water etc - may still need to update produced JSON keys
    Follows arbitrary methods previously used!
    '''
    phases = {"water": "Water",
              "solar": "Solar",
              "teloaded": "TeLoaded",
              "partialscint": "PartialScint"}
    if macro.endswith('.mac'):
        macro = macro[:-4]
    bits = macro.split('_')
    return '_'.join(b.capitalize() for b in bits)


def download_production_request(request):
    '''Download either JSON or CSV file based on production request form
    '''

    output = {}
    output['rat_v'] = request.GET['rat_version']
    output['modules'] = []
    templates = set()
    request_type, _, file_format = request.GET['submit'].partition('-')

    macro_keys = request.GET.getlist('macro_key')

    if request_type == "time":
        page = "production/request_by_time.html"
        RequestFormset = formset_factory(MacroFormByTime, BaseRequestFormset, extra=0)
    else:
        page = "production/request_by_number.html"
        RequestFormset = formset_factory(MacroFormByNumber, BaseRequestFormset, extra=0)

    formset = RequestFormset(macro_keys, request.GET)
    if formset.is_valid():
        
        for key in request.GET.getlist("macro_key"):
            if request_type == "time":
                info = {"module": mangle_module_name(request.GET["{0}-phase".format(key)],
                                                     request.GET["{0}-macro".format(key)]),                
                        "t_run": request.GET["runDuration"],
                        "t_format": request.GET["runFormat"],
                        "n_runs": request.GET["{0}-n_runs".format(key)],
                        "template": {}}
            else:
                info = {"module": mangle_module_name(request.GET["{0}-phase".format(key)],
                                                     request.GET["{0}-macro".format(key)]),                
                        "ev_per_run": request.GET["{0}-ev_per_run".format(key)],
                        "n_runs": request.GET["{0}-n_runs".format(key)],
                        "template": {}}
            # Extracting the rate into a separate field might have been silly!
            try:
                info["template"]["rate"] = float(request.GET["{0}-rate".format(key)])
                templates.add("rate")
            except (KeyError, ValueError):
                # Catch request by number (where no rate input) 
                # And request by time (where rate value may be "FIXED")
                pass
            for template in request.GET.getlist('{0}_template_names'.format(key)):
                info['template'][template] = request.GET['{0}-{1}'.format(key, template)]
                templates.add(template)
            output['modules'].append(info)
    
        template_keys = list(templates)
        if request_type == "time":
            csv_keys = ['module', 't_run', 't_format', 'n_runs']
        else:
            csv_keys = ['module', 'ev_per_run', 'n_runs']
    
        if file_format.lower() == 'json':
            # Download a JSON file
            response = HttpResponse(content_type='application/json')
            response['Content-Disposition'] = 'attachment; filename=filelist.js'
            response.write(json.dumps(output, indent=2, sort_keys=True))
        elif file_format.lower() == 'csv':
            # Download a CSV file (to check in spreadsheet only)
            # list as: module, t_run, t_format, n_runs, templates ....
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=filelist.csv'
            writer = csv.writer(response)
            writer.writerow(['rat_v', output['rat_v']])
            writer.writerow(csv_keys + template_keys)
            for entry in output['modules']:
                row = [entry[k] for k in csv_keys]
                for t in template_keys:
                    try:
                        row = row + [entry['template'][t]]
                    except KeyError:
                        row = row + ['']
                writer.writerow(row)
        else:
            raise ValueError("Unknown file format {0}".format(file_format))
        return response

    return render(
        request,
        page,
        {'formset': formset,
         'rat_version': request.GET['rat_version']})
