from django.http import HttpResponse
from django.shortcuts import redirect
from django.template import RequestContext, Context, loader
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.conf import settings
from snopldotus.models import UserProfile
from django.db import connections

from snopldotus.xdr_registry import registry

import base64
import csv
from datetime import datetime, timedelta
import httplib
import hashlib
import json
import mimetypes
from operator import itemgetter
import re
import requests
import tempfile
import StringIO

def index(request):
    if request.user.is_authenticated():
        if "Firefox" in request.META['HTTP_USER_AGENT']:
            t = loader.get_template('snopl.us/index_aquabuddy.html')
        else:
            t = loader.get_template('snopl.us/index.html')
        request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()
        c = RequestContext(request, {})
        return HttpResponse(t.render(c))
    else:
        t = loader.get_template('snopl.us/index_public.html')
        c = Context()
        return HttpResponse(t.render(c))


def xdr_validate(request):
    params = request.GET
    try:
        if registry.validate(params['username'], params['application'], params['xdr_token']):
            return HttpResponse('{"ok": true}')
    except Exception:
        pass

    return HttpResponse('{"ok": false}')


def logout_view(request):
    logout(request)
    return redirect('/')


@login_required
def user(request, name):
    t = loader.get_template('snopl.us/user.html')
    request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()
    user = User.objects.filter(username__exact=name)[0]
    try:
        profile = user.get_profile()
        profile.gravatar_hash = hashlib.md5(user.email.strip().lower()).hexdigest()
    except UserProfile.DoesNotExist:
        profile = None

    c = RequestContext(request, {
        'display_user': user,
        'display_profile': profile,
    })
    return HttpResponse(t.render(c))


@login_required
def collaboration_list(request):
    t = loader.get_template('snopl.us/collaboration_list.html')
    request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()

    people = User.objects.all().order_by('-last_name')

    for person in people:
        person.gravatar_hash = hashlib.md5(person.email.strip().lower()).hexdigest()

    c = RequestContext(request, {
        'people': people
    })
    return HttpResponse(t.render(c))


@login_required
def calls(request):
    t = loader.get_template('snopl.us/calls.html')
    request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()

    people = User.objects.all().order_by('-last_name')

    for person in people:
        person.gravatar_hash = hashlib.md5(person.email.strip().lower()).hexdigest()

    c = RequestContext(request, {
        'people': people
    })
    return HttpResponse(t.render(c))


@login_required
def phone_list(request):
    t = loader.get_template('snopl.us/phone_list.html')
    request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()

    c = RequestContext(request, {})
    return HttpResponse(t.render(c))


@login_required
def oncall(request):
    t = loader.get_template('snopl.us/on_call_expert_list.html')
    request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()

    c = RequestContext(request, {})
    return HttpResponse(t.render(c))


@login_required
def build_tests(request, db):
    t = loader.get_template('snopl.us/build_test_list.html')
    request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()

    conn = httplib.HTTPConnection(settings.PYTUNIA_SERVER)
    headers = {
        'Content-type': 'application/json',
    }
    if settings.PYTUNIA_AUTH is not None:
        headers['Authorization'] = 'Basic %s' % base64.encodestring(settings.PYTUNIA_AUTH)[:-1]

    if db == 'ondemand':
        dbpath = 'pytunia-ondemand'
        uipath = 'ondemand'
        type_string = 'On-Demand'
    elif db == 'production':
        dbpath = 'pytunia'
        uipath = 'build'
        type_string = 'Production'

    conn.request('GET', '/%s/_design/pytunia/_list/index/summary?descending=true&limit=3000' % dbpath, headers=headers)
    response = conn.getresponse()

    data = json.loads(response.read())

    tasks = []
    first_test = 0
    last_task = -1

    c = RequestContext(request, {
        'type': type_string,
        'path': uipath,
        'response': response,
        'data': data
    })
    return HttpResponse(t.render(c))

@login_required
def btdev(request, db):
    t = loader.get_template('snopl.us/build_test_list.html')
    request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()

    conn = httplib.HTTPConnection(settings.PYTUNIA_SERVER)
    headers = {
        'Content-type': 'application/json',
    }
    if settings.PYTUNIA_AUTH is not None:
        headers['Authorization'] = 'Basic %s' % base64.encodestring(settings.PYTUNIA_AUTH)[:-1]

    if db == 'ondemand':
        dbpath = 'pytunia-ondemand'
        uipath = 'ondemand'
        type_string = 'On-Demand'
    elif db == 'production':
        dbpath = 'pytunia'
        uipath = 'build'
        type_string = 'Production'

    conn.request('GET', '/%s/_design/pytunia/_view/summary?descending=true&skip=0&limit=100' % dbpath, headers=headers)
    response = conn.getresponse()

    data = json.loads(response.read())

    c = RequestContext(request, {
        'type': type_string,
        'path': uipath,
        'data': data
    })
    return HttpResponse(t.render(c))


@login_required
def build_test(request, record_id, db):
    t = loader.get_template('snopl.us/build_test.html')
    request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()

    conn = httplib.HTTPConnection(settings.PYTUNIA_SERVER)
    headers = {
        'Content-type': 'application/json',
    }
    if settings.PYTUNIA_AUTH is not None:
        headers['Authorization'] = 'Basic %s' % base64.encodestring(settings.PYTUNIA_AUTH)[:-1]

    if db == 'ondemand':
        dbpath = 'pytunia-ondemand'
        uipath = 'ondemand'
        type_string = 'On-Demand'
    elif db == 'production':
        dbpath = 'pytunia'
        uipath = 'build'
        type_string = 'Production'

    conn.request('GET', '/%s/_design/pytunia/_list/record/tasks_by_record?startkey=["%s"]&endkey=["%s",{}]' % (dbpath, record_id, record_id), headers=headers)
    response = conn.getresponse()

    data = json.loads(response.read())

    c = RequestContext(request, {
        'record': data,
        'type': type_string,
        'path': uipath,
        'response': response,
    })
    return HttpResponse(t.render(c))


@login_required
def build_task(request, task, db):
    t = loader.get_template('snopl.us/build_task.html')
    request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()

    conn = httplib.HTTPConnection(settings.PYTUNIA_SERVER)
    headers = {
        'Content-type': 'application/json',
    }
    if settings.PYTUNIA_AUTH is not None:
        headers['Authorization'] = 'Basic %s' % base64.encodestring(settings.PYTUNIA_AUTH)[:-1]

    if db == 'ondemand':
        dbpath = 'pytunia-ondemand'
        uipath = 'ondemand'
        type_string = 'On-Demand'
    elif db == 'production':
        dbpath = 'pytunia'
        uipath = 'build'
        type_string = 'Production'
    conn.request('GET', '/%s/_design/pytunia/_list/task/tasks_by_name?startkey=["%s",{}]&endkey=["%s"]&descending=true' % (dbpath, task, task), headers=headers)
    response = conn.getresponse()

    data = json.loads(response.read())

    c = RequestContext(request, {
        'data': data,
        'task': task,
        'type': type_string,
        'path': uipath,
        'response': response,
    })
    return HttpResponse(t.render(c))


@login_required
def build_attachment(request, db, task, path):
    conn = httplib.HTTPConnection(settings.PYTUNIA_SERVER)
    headers = {
        'Content-type': 'application/json',
    }
    if settings.PYTUNIA_AUTH is not None:
        headers['Authorization'] = 'Basic %s' % base64.encodestring(settings.PYTUNIA_AUTH)[:-1]

    if db == 'Production':
        dbname = 'pytunia'
    else:
        dbname = 'pytunia-ondemand'

    print '/%s/%s/%s' % (dbname, task, path)
    conn.request('GET',
                 '/%s/%s/%s' % (dbname, task, path),
                 headers=headers)
    response = conn.getresponse()

    data = response.read()
    with tempfile.NamedTemporaryFile() as f:
        f.write(data)
        mime = mimetypes.guess_type(f.name)
        return HttpResponse(data, mimetype=mime)


def load_server_replications(name, server, auth):
    headers = {
        'Authorization': ('Basic %s' % auth.encode('base64')).rstrip(),
        'Content-type': 'application/json'
    }

    error_dict = {
        'name': name,
        'url': server,
        'replications': [],
        'error': 'Unable to connect to server'
    }

    # Parse the replication documents from /_replicator
    try:
        replications = requests.get(server + '/_replicator/_all_docs?include_docs=true', headers=headers)
    except Exception:
        return error_dict

    reps = filter(lambda x: 'source' in x, [x['doc'] for x in replications.json()['rows']])
    reps = sorted(reps, key=itemgetter('source'))
    
    # Parse the active tasks from /_active_tasks
    try:
        active_tasks = requests.get(server + '/_active_tasks', headers=headers)
    except Exception:
        return error_dict

    tasks = {}
    for at in active_tasks.json():
        rep_id = at.get('replication_id', '')
        if '+' in rep_id:
            r_id = rep_id.split('+')[0]
        else:
            r_id = rep_id
    
        tasks[r_id] = at
    
    # Merge
    for rep in reps:
        user, pw = auth.split(':')
        rep['source'] = rep['source'].replace(auth, user + ':*****')

        if '_replication_id' in rep:
            task = tasks.get(rep['_replication_id'])
            if task:
                rep.update(task)

        for k, v in rep.items():
            if k.startswith('_'):
                rep[k.lstrip('_')] = v

        update = rep.get('updated_on', None)
        if update:
            rep['age'] = datetime.now() - datetime.fromtimestamp(update)
        else:
            rep['age'] = 'Unknown'

    return {
        'name': name,
        'url': server,
        'replications': reps,
    }


def get_postgres_status():
    """
    Returns a list of results about the streaming status for slaves
    streaming from dbug.
    """
    cursor = connections['postgres'].cursor()

    cursor.execute("select * from streaming_status()")

    columns = [col[0] for col in cursor.description]

    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def load_haproxy_status(name, url, stats_url, auth):
    headers = {
        'Authorization': ('Basic %s' % auth.encode('base64')).rstrip(),
        'Content-type': 'text/csv'
    }

    error_dict = {
        'name': name,
        'url': url,
        'rows': [],
        'error': 'Unable to connect to server'
    }

    try:
        stats = requests.get(stats_url, headers=headers)
    except Exception:
        return error_dict

    f = StringIO.StringIO(stats.text)
    rows = []
    for row in csv.reader(f):
        if row[0].startswith('#'):
            continue
        uptime = timedelta(seconds=float(row[23])) if row[23] != '' else ''
        rows.append({
            'name': row[0],
            'service': row[1],
            'bytes_in': row[8],
            'bytes_out': row[9],
            'status': row[17],
            'active': row[19],
            'backup': row[20],
            'uptime': uptime,
            'check': row[36],
        })
    return {
        'name': name,
        'url': url,
        'rows': rows,
    }


@login_required
def db_replication_status(request):
    t = loader.get_template('snopl.us/db_replication_status.html')
    request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()

    couchdb_data = map(lambda x: load_server_replications(*x), settings.COUCHDB_REPLICATION_SERVERS)
    haproxy_data = map(lambda x: load_haproxy_status(*x), settings.HAPROXY_SERVERS)

    # FIXME Clean up
    for row in couchdb_data:
        for rep in row.get('replications', []):
            s = rep['source']
            pos1 = s.find('://')
            pos2 = s.find('@')
            if pos2 > 0:
                s = s[:pos1] + '://' + s[pos2+1:]
            rep['source'] = s

    for row in couchdb_data:
        for rep in row.get('replications', []):
            s = rep['target']
            pos1 = s.find('://')
            pos2 = s.find('@')
            if pos2 > 0:
                s = s[:pos1] + '://' + s[pos2+1:]
            rep['target'] = s

    dict_ = {
        'couchdb_servers': couchdb_data,
        'haproxy_servers': haproxy_data,
    }

    try:
        dict_['pg_status'] = get_postgres_status()
    except Exception as e:
        dict_['pg_error'] = str(e)

    c = RequestContext(request, dict_)

    return HttpResponse(t.render(c))


@login_required
def restart_replications(request, server_name):
    # Superusers only
    if not request.user.is_superuser:
        return HttpResponse(status=401)

    # Find a server in the known list by name. This is a little strange but
    # avoids putting auth information in the HTML.
    server = None
    for s in settings.COUCHDB_REPLICATION_SERVERS:
        if s[0] == server_name:
            server = load_server_replications(*s)
            break
    if server is None:
        data = {'error': 'Server unknown'}
        return HttpResonse(json.dumps(data), status=400)

    def restart_replication(url, auth):
        headers = {
            'Authorization': 'Basic %s' % auth.encode('base64').rstrip(),
            'Content-type': 'application/json'
        }
        doc = requests.get(url, headers=headers).json()
        for k in ['_replication_id',
                  '_replication_state',
                  '_replication_state_reason',
                  '_replication_state_time']:
            if k in doc:
                del doc[k]
        req = requests.put(url, data=json.dumps(doc), headers=headers)
        if req.status_code >= 400:
            raise Exception('Restart returned %i', req.status_code)

    # Find all the errored replications and restart them
    stopped = []
    errors = []
    replications = server.get('replications', [])
    for replication in replications:
        if replication.get('_replication_state') == 'error':
            doc_id = replication['_id']
            stopped.append(doc_id)
            url = '%s/_replicator/%s' % (server['url'], doc_id)

            try:
                restart_replication(url, s[2])
            except Exception:
                errors.append(doc_id)

    data = {
        #'replications': replications,
        'restarted': stopped,
        'failed': errors
    }
    return HttpResponse(json.dumps(data))

