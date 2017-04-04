from django.http import HttpResponse
from django.template import RequestContext, Context, loader
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import condition
from django.conf import settings
from django.shortcuts import redirect
from django.core.urlresolvers import reverse
from django.utils.http import urlquote

import os
import sys
import socket
import getpass
import subprocess
import smtplib
import uuid
import tempfile
import mimetypes
import httplib
import base64
import json
import hashlib
import re
from datetime import datetime
from urllib import quote

import pytz
import dateutil.parser

from run.rundoc import GET, make_headers

tz = pytz.timezone(settings.PHILA_TZ)
fmt = '%Y/%m/%d %H:%M:%S (%Z)'

def make_db_connection():
    '''Helper function: Connect to CouchDB'''
    conn = httplib.HTTPConnection(settings.PHILA_SERVER)
    headers = {
        'Content-type': 'application/json',
    }
    if settings.PHILA_AUTH is not None:
        authstring = 'Basic %s' % base64.encodestring(settings.PHILA_AUTH)[:-1]
        headers['Authorization'] = authstring
    return conn, headers


def email(recipients, subject, message, sender=None):
    '''Helper function: Send an email via SMTP.

    If the sender address is not specified, use the current user info.

    :param recipients: List of email addresses to send to
    :param subject: Subject line
    :param message: Message body
    :param sender: Email address of sender
    '''
    server = getattr(settings, 'PHILA_SMTP_SERVER', None)
    if server is None:
        return

    if sender is None:
        username = getpass.getuser()
        hostname = socket.getfqdn()
        sender = '%s@%s' % (username, hostname)

    message = ('Subject: %s' % subject) + '\n\n' + message

    try:
        smtp = smtplib.SMTP(server)
        smtp.sendmail(sender, recipients, message)
    except smtplib.SMTPException as e:
        sys.stderr.write('SMTP error: ' + str(e))
    except socket.error as e:
        sys.stderr.write('SMTP error: ' + str(e))


def get_report(report_id):
    '''Helper function: Get the report as a Python object.'''
    # Blocks
    url = '/phila/_design/phila/_view/report?startkey=["%s"]&endkey=["%s",{}]'
    conn, headers = make_db_connection()
    conn.request('GET', url % (report_id, report_id), headers=headers)
    response = conn.getresponse()
    blocks = json.loads(response.read())['rows']

    for block in blocks:
        # Can't use attributes starting with '_' in Django templates
        if '_attachments' in block['value']:
            block['value']['attachments'] = block['value']['_attachments']
        block['value']['id'] = block['id']
        block['value']['rev'] = block['value']['_rev']

        created = block['value']['created']
        utctime = dateutil.parser.parse(created, fuzzy=True)
        if utctime.tzinfo is None:
            utctime = (pytz.timezone('UTC')).localize(utctime)
        block['value']['created'] = utctime.astimezone(tz).strftime(fmt)

    # Report and comments
    conn, headers = make_db_connection()
    conn.request('GET', '/phila/%s' % report_id, headers=headers)
    response = conn.getresponse()
    if not response.status < 400:
        raise Exception('Report not found')
    report = json.loads(response.read())

    context = {
        'id': report_id,
        'report': report,
        'blocks': blocks
    }

    return context


@login_required
def index(request):
    '''Display a list of shift reports.

    :param request: Django request object
    :returns: HTML HttpResponse
    '''
    t = loader.get_template('philadelphia/index.html')
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    start = int(request.GET.get('start', 0))
    limit = int(request.GET.get('limit', 15))

    conn, headers = make_db_connection()
    conn.request('GET',
                 '/phila/_design/phila/_view/reports_by_date?descending=true&skip=%i&limit=%i' % (start, limit),
                 headers=headers)
    response = conn.getresponse()
    data = json.loads(response.read())
    total_reports = data['total_rows']

    reports = []
    for row in data['rows']:
        conn, headers = make_db_connection()
        conn.request('GET',
                     '/phila/_design/phila/_view/reports?group=true&startkey=["%s"]&endkey=["%s",{}]' % (row['id'], row['id']),
                 headers=headers)
        response = conn.getresponse()
        data = json.loads(response.read())
        reports.append(data['rows'][0]['value'])

    for report in reports:
        try:
            report['short_id'] = report['id'][-8:]
        except KeyError:
            report['short_id'] = 'Invalid ID'

        try:
            created = report['created']
            # Hack: Reports created in client JS Phila have all kinds of wacky
            # time formats which dateutil.parser doesn't like
            created = created.replace('Eastern Standard Time', 'EST')
            created = created.replace('Eastern Daylight Time', 'EDT')
            created = created.replace('GMT Standard Time', 'GMT')
            utctime = dateutil.parser.parse(created)
            if utctime.tzinfo is None:
                utctime = (pytz.timezone('UTC')).localize(utctime)
            report['created_pretty'] = utctime.astimezone(tz).strftime(fmt)
            report['created_iso'] = utctime.astimezone(tz).isoformat()

	except Exception:
            report['created_iso'] = '0'
            report['created_pretty'] = 'Invalid date'

    reports = sorted(reports, key=lambda x: x['created_iso'], reverse=True)
    reports = filter(lambda x: x['short_id'] != 'Invalid ID', reports)

    c = RequestContext(request, {
        'reports': reports,
        'total_reports': total_reports,
        'previous_start': max(start - limit, 0),
        'next_start': start + limit,
        'start': start,
        'limit': limit
    })
    return HttpResponse(t.render(c))


@login_required
def report(request, report_id):
    '''Display a shift report.

    If 'json' is in the query string, return as JSON, otherwise return HTML.

    :param request: Django request object
    :param report_id: CouchDB document ID for the report
    :returns: HTML HttpResponse
    '''
    t = loader.get_template('philadelphia/view.html')
    request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()
    try:
        context = get_report(report_id)
    except Exception:
        raise
        return redirect('/shift')

    if request.GET.get('json', False):
        return HttpResponse(json.dumps(context), mimetype='application/json')

    for block in context['blocks']:
        if not block['value']['name'] in ['Basic Information', 'Text Entry']:
            block['collapsed'] = True

    context['index_start'] = int(request.GET.get('index_start', 0))
    c = RequestContext(request, context)
    return HttpResponse(t.render(c))


@login_required
def pdf(request, report_id):
    '''Produce a downloadable PDF copy of a report.

    This requires 'pdflatex' in the path. We create LaTeX source with a Django
    template, write it to a temporary file to 'pdflatex' it, and return the
    contents of the output file.

    :param request: Django request object
    :param report_id: CouchDB document ID for the report
    :returns: HttpResponse (application/pdf)
    '''
    t = loader.get_template('philadelphia/report.tex')

    try:
        context = get_report(report_id)
    except Exception:
        return redirect('/shift')
    authors = 'Unknown Authors'
    date = 'Unknown Date'

    for block in context['blocks']:
        for field in block['value']['fields']:
            if 'value' in field:
                field['value'] = field['value'].replace('%', '\\%')
            if block['value']['name'].endswith('Basic Information'):
                if field['name'] == 'Crew' and 'value' in field:
                    authors = field['value']

    context['authors'] = authors

    utctime = dateutil.parser.parse(context['report']['created'])
    if utctime.tzinfo is None:
        utctime = tz.localize(utctime)

    context['date'] = \
        utctime.astimezone(pytz.timezone(settings.PHILA_TZ)).strftime(fmt)
    c = RequestContext(request, context)

    td = tempfile.mkdtemp()
    pdffile = None
    pdfdata = ''
    with tempfile.NamedTemporaryFile(dir=td, suffix='.tex', mode='r+w') as f:
        f.write(t.render(c))
        f.seek(0)
        subprocess.check_output(['pdflatex', f.name], cwd=td)
        with open(os.path.splitext(f.name)[0] + '.pdf') as pdffile:
            pdfdata = pdffile.read()
    del td

    return HttpResponse(pdfdata, mimetype='application/pdf')


@login_required
def edit(request, report_id):
    '''Open a report in the editor view.

    :param request: Django request object
    :param report_id: CouchDB document ID
    :returns: HTML HttpResponse
    '''
    t = loader.get_template('philadelphia/edit.html')
    request.user.gravatar_hash = hashlib.md5(request.user.email.strip().lower()).hexdigest()
    try:
        context = get_report(report_id)
    except Exception:
        return redirect('/shift')

    # No touching submitted reports!
    if context['report'].get('submitted', False):
        return redirect('/shift')

    # Get the list of templates for the 'add new block' dialog
    url = '/phila/_design/phila/_view/templates'
    conn, headers = make_db_connection()
    conn.request('GET', url, headers=headers)
    response = conn.getresponse()
    templates = json.loads(response.read())['rows']
    context['templates'] = templates

    # Every session has a unique editor ID
    context['editor_id'] = uuid.uuid4().hex

    c = RequestContext(request, context)
    return HttpResponse(t.render(c))


@login_required
def attachment(request, doc_id=None, path=None):
    '''Fetch/post an attachment on a CouchDB document.

    For POST requests, create the attachment and return the HTML for the
    table row.

    :todo: Move this up a level, as it's useful for more than shift reports.

    :param request: Django request object
    :param report_id: CouchDB document ID, for GET
    :param path: Path to the attachment within the document, for GET
    :returns: HttpResponse with appropriate MIME type
    '''
    if request.method == 'GET':
        conn, headers = make_db_connection()
        url = '/phila/%s/%s'
        conn.request('GET', url % (doc_id, urlquote(path)), headers=headers)
        response = conn.getresponse()
 
        # Write data to a file in order to guess the MIME type
        data = response.read()
        with tempfile.NamedTemporaryFile() as f:
            f.write(data)
            mime = mimetypes.guess_type(f.name)
            return HttpResponse(data, mimetype=mime)

    if request.method == 'POST':
        doc_id = request.POST['target_doc_id']
        doc_rev = request.POST['target_doc_rev']
        attachment = request.FILES['_attachments']

        conn, headers = make_db_connection()
        url = '/phila/' + doc_id
        conn.request('GET', url, headers=headers)
        response = conn.getresponse()
        doc = json.loads(response.read())

        # Don't touch submitted reports
        if doc['type'] == 'report':
            if doc.get('submitted', False):
                return HttpResponse(status=401)
        else:
            if not doc['type'] == 'block':
                return HttpResponse('Document is not a block!', status=400)
            conn, headers = make_db_connection()
            url = '/phila/' + doc['report_id']
            conn.request('GET', url, headers=headers)
            response = conn.getresponse()
            report = json.loads(response.read())
            if report.get('submitted', False):
                return HttpResponse(status=401)

        data = attachment.read().encode('base64')
        with tempfile.NamedTemporaryFile() as f:
            for chunk in attachment.chunks():
                f.write(chunk)
            f.seek(0)
            mime = str(mimetypes.guess_type(f.name)[0])

        attachments = doc.get('_attachments', {})
        attachments[attachment.name] = {
            'content-type': mime,
            'data': data
        }
        doc['_attachments'] = attachments

        url = '/phila/%s?rev=%s' % (doc_id, doc_rev)
        conn, headers = make_db_connection()
        conn.request('PUT', url, json.dumps(doc), headers=headers)
        response = conn.getresponse()
        if not response.status < 400:
            return HttpResponse(response.read(), status=response.status)

        data = json.loads(response.read())

        t = loader.get_template('philadelphia/editor/attachment.html')
        c = RequestContext(request, {
            'attachment': attachment.name,
            'blk': {
                'value': {
                    'id': doc_id
                }
            }
        })

        d = {
            'html': t.render(c),
            'rev': data['rev']
        }

        return HttpResponse(json.dumps(d), mimetype='application/json')


@login_required
def attachment_delete(request, doc_id):
    if request.method == 'POST':
        conn, headers = make_db_connection()
        url = '/phila/' + doc_id
        conn.request('GET', url, headers=headers)
        response = conn.getresponse()
        doc = json.loads(response.read())

        # Don't touch submitted reports
        if doc['type'] == 'report':
            if doc.get('submitted', False):
                return HttpResponse(status=401)
        else:
            if not doc['type'] == 'block':
                return HttpResponse('Document is not a block!', status=400)
            conn, headers = make_db_connection()
            url = '/phila/' + doc['report_id']
            conn.request('GET', url, headers=headers)
            response = conn.getresponse()
            report = json.loads(response.read())
            if report.get('submitted', False):
                return HttpResponse(status=401)

        name = request.POST['name']
        rev = request.POST['rev']
        conn, headers = make_db_connection()
        url = '/phila/' + doc_id + '/' + urlquote(name) + '?rev=' + rev
        conn.request('DELETE', url, headers=headers)
        response = conn.getresponse()
        return HttpResponse(response.read(), response.status)


@login_required
def comment(request, doc_id, index=None):
    '''Post a comment to a shift report.

    Returns JSON if 'json' is in the query string, else an HTML snippet.

    :param request: Django request object
    :param doc_id: CouchDB document ID
    :param index: Index of the comment to grab, used only for GET requests
    :returns: HttpResponse
    '''
    if request.method == 'GET':
        # Get the report document
        conn, headers = make_db_connection()
        url = '/phila/%s' % doc_id
        conn.request('GET', url, headers=headers)
        response = conn.getresponse()
        if not response.status < 400:
            return HttpResponse(status=response.status)
        report = json.loads(response.read())
        comment = report['comments'][int(index.strip('/'))]

    if request.method == 'POST':
        # Get the report document
        conn, headers = make_db_connection()
        url = '/phila/%s'
        conn.request('GET', url % doc_id, headers=headers)
        response = conn.getresponse()
        if not response.status < 400:
            return HttpResponse(status=response.status)
        report = json.loads(response.read())

        # Append comment
        now = datetime.now(tz=pytz.timezone(settings.PHILA_TZ)).isoformat()
        comment = {
            'name': request.POST.get("name", "Anonymous"),
            'text': request.POST.get("text", ""),
            'created': now
        }
        if 'comments' in report:
            report['comments'].append(comment)
        else:
            report['comments'] = [comment]

        # Post it
        conn.request('PUT', url % doc_id, json.dumps(report), headers=headers)
        response = conn.getresponse()
        if not response.status < 400:
            return HttpResponse(status=response.status)

    # Return the comment HTML to append to the DOM
    t = loader.get_template('philadelphia/comment.html')
    c = RequestContext(request, {'comment': comment})

    if request.GET.get('json', False):
        comment['html'] = t.render(c)
        return HttpResponse(json.dumps(comment), mimetype='application/json')

    return HttpResponse(t.render(c))


@login_required
def new(request):
    '''Create a new report.

    This creates the DB documents and redirects to the editor.

    :param request: The Django request object
    :returns: (Temporary) redirect HttpResponse
    '''
    report_id = uuid.uuid4().hex

    report = {
        '_id': report_id,
        'type': 'report',
        'created': datetime.utcnow().isoformat(),
        'comments': []
    }

    url = '/phila/%s'
    conn, headers = make_db_connection()
    conn.request('PUT', url % report['_id'], json.dumps(report), headers=headers)
    response = conn.getresponse()
    if not response.status < 400:
        return HttpResponse(status=response.status)

    # Load default blocks, sorted by priority
    url = '/phila/_design/phila/_view/templates'
    conn, headers = make_db_connection()
    conn.request('GET', url, headers=headers)
    response = conn.getresponse()
    templates = json.loads(response.read())['rows']
    default_templates = []
    for row in templates:
        template = row['value']
        if 'default' in template and template['default']:
            default_templates.append(template)

    default_templates = sorted(default_templates,
                               key=lambda x: x.get('priority', 0),
                               reverse=True)

    blocks = []
    for template in default_templates:
        block = {
            '_id': uuid.uuid4().hex,
            'type': 'block',
            'report_id': report_id,
            'name': template['name'],
            'created': tz.localize(datetime.now()).isoformat(),
            'fields': template['fields']
        }
        blocks.append({'value': block})

        # Add block document to DB
        url = '/phila/%s'
        conn, headers = make_db_connection()
        conn.request('PUT',
                     url % block['_id'],
                     json.dumps(block),
                     headers=headers)

        response = conn.getresponse()
        if not response.status < 400:
            return HttpResponse(status=response.status)

    return redirect('/shift/edit/%s' % report_id)


@login_required
def block(request, doc_id=None):
    '''Load or create a block.

    Build a new block from a template or load a block from the DB, and
    return the HTML for it.

    :param request: The Django request object
    :param doc_id: ID of the block to get, used only for GET requests
    :returns: HTML HttpResponse
    '''
    if request.method == 'GET':
        conn, headers = make_db_connection()
        url = '/phila/%s' % doc_id
        conn.request('GET', url, headers=headers)
        response = conn.getresponse()
        block = json.loads(response.read())
        if not block['type'] == 'block':
            return HttpResponse(status=400)
        if '_attachments' in block:
            block['attachments'] = block['_attachments']

        block = {'value': block}

    if request.method == 'POST':
        # Load the template
        conn, headers = make_db_connection()
        url = '/phila/_design/phila/_view/templates'
        conn.request('GET', url, headers=headers)
        response = conn.getresponse()
        templates = json.loads(response.read())['rows']
        template = None
        for row in templates:
            temp = row['value']
            if temp['name'] == request.POST['name']:
                template = temp
                break

        block = {
            'value': {
                '_id': uuid.uuid4().hex,
                'type': 'block',
                'report_id': request.POST['report_id'],
                'name': template['name'],
                'created': tz.localize(datetime.now()).isoformat(),
                'updated': tz.localize(datetime.now()).isoformat(),
                'fields': template['fields']
            }
        }

        # Add the block to the DB
        conn.request('PUT', '/phila/%s' % block['value']['_id'], json.dumps(block['value']), headers=headers)
        response = conn.getresponse()
        if not response.status < 400:
            return HttpResponse(status=response.status)
        data = json.loads(response.read())
        block['value']['_rev'] = data['rev']

    # Pretty up the timestamp for display
    created = block['value']['created']
    utctime = dateutil.parser.parse(created, fuzzy=True)
    if utctime.tzinfo is None:
        utctime = (pytz.timezone('UTC')).localize(utctime)
    block['value']['created'] = utctime.astimezone(tz).strftime(fmt)

    # Return the block HTML to append to the DOM
    t = loader.get_template('philadelphia/editor/block.html')
    block_id = block['value']['id'] = block['value']['_id']
    block_rev = block['value']['rev'] = block['value']['_rev']
    c = RequestContext(request, {'blk': block})
    data = json.dumps({'html': t.render(c), 'id': block_id, 'rev': block_rev})
    return HttpResponse(data, mimetype='application/json')


@login_required
def delete(request, doc_id):
    '''Delete a DB document.

    Only superusers are allowed to delete reports, and no one is allowed to
    delete submitted reports. When deleting a report, all of the associated
    blocks are deleted, too.

    :param request: Django request object
    :param doc_id: ID of the document to delete
    :returns: HttpResponse with a status only
    '''
    if not request.method == 'DELETE':
        return HttpResponse(status=405)

    # Load the document
    conn, headers = make_db_connection()
    url = '/phila/%s' % doc_id
    conn.request('GET', url, headers=headers)
    response = conn.getresponse()
    doc = json.loads(response.read())

    to_delete = [(doc_id, doc['_rev'])]

    if doc['type'] == 'report':
        if not request.user.is_superuser or doc.get('submitted', False):
            return HttpResponse(status=401)

        # Also delete blocks when deleting a report
        url = '/phila/_design/phila/_view/report?startkey=["%s"]&endkey=["%s",{}]'
        conn.request('GET', url % (doc_id, doc_id), headers=headers)
        response = conn.getresponse()
        blocks = json.loads(response.read())['rows']
        to_delete.extend([(b['id'], b['value']['_rev']) for b in blocks])

    elif doc['type'] == 'block':
        conn, headers = make_db_connection()
        url = '/phila/%s' % doc['report_id']
        conn.request('GET', url, headers=headers)
        response = conn.getresponse()
        report = json.loads(response.read())
        if report.get('submitted', False):
            return HttpResponse(status=401)

    elif doc.get('type', '') != 'board':
        return HttpResponse(status=400)

    for (doc_id, rev) in to_delete:
        conn, headers = make_db_connection()
        url = '/phila/%s?rev=%s' % (doc_id, rev)
        conn.request('DELETE', url, headers=headers)
        response = conn.getresponse()

    return HttpResponse(status=response.status)


@login_required
def save(request):
    '''Save a document to the DB.

    The document to save is given in the POST data with keys id, rev,
    editor_id, and fields. If key 'trample' is true, the revision is ignored
    and the document is saved even if it isn't the latest.

    The JSON reponse contains:

        {
            ok: true,
            id: Document ID,
            rev: Document revision
        }

    :param request: Django request object
    :returns: JSON HttpResponse
    '''
    if request.method == 'POST':
        fields = json.loads(request.POST['fields'])
        doc_id = request.POST['id']
        rev = request.POST['rev']
        editor_id = request.POST['editor_id']
        trample = request.POST['trample']

        conn, headers = make_db_connection()
        url = '/phila/%s' % doc_id
        conn.request('GET', url, headers=headers)
        response = conn.getresponse()
        doc = json.loads(response.read())
        report_id = doc['report_id']

        # Don't touch submitted reports
        conn, headers = make_db_connection()
        url = '/phila/%s' % report_id
        conn.request('GET', url, headers=headers)
        response = conn.getresponse()
        report = json.loads(response.read())
        if report.get('submitted', False):
            return HttpResponse(status=401)

        doc['editor_id'] = editor_id
        doc['fields'] = fields

        doc['updated'] = tz.localize(datetime.now()).isoformat()

        if trample:
            rev = doc['_rev']

        conn.request('PUT',
                     '/phila/%s?rev=%s' % (doc_id, rev),
                     json.dumps(doc),
                     headers=headers)
        response = conn.getresponse()
        data = json.loads(response.read())
        if not response.status < 400:
            return HttpResponse(status=response.status)

        data = {
            "ok": True,
            "id": doc_id,
            "rev": data['rev']
        }

        return HttpResponse(json.dumps(data), mimetype='application/json')


@login_required
def submit(request, report_id):
    '''Submit a report.

    This prevents further editing (including deletion) and sends out an email
    notification.

    :param request: Django request object
    :param report_id: ID of the report to save
    :returns: HttpResponse with a status only
    '''
    # Check that this is a submit-able document
    conn, headers = make_db_connection()
    url = '/phila/%s' % report_id
    conn.request('GET', url, headers=headers)
    response = conn.getresponse()
    doc = json.loads(response.read())
    if not doc['type'] == 'report':
        return HttpResponse(status=400)
    if doc.get('submitted', False):
        return HttpResponse(status=401)

    doc['submitted'] = True
    conn.request('PUT',
                 '/phila/%s?rev=%s' % (report_id, doc['_rev']),
                 json.dumps(doc),
                 headers=headers)
    response = conn.getresponse()
    if not response.status < 400:
        return HttpResponse(status=response.status)

    subject = '[philadelphia] Shift Report ' + doc['_id'][-8:]
    view_url = reverse('philadelphia.views.report', args=(report_id,))

    message_data = {
        'created': doc['created'],
        'id': report_id,
        'host': socket.getfqdn(),
        'dbname': 'phila',
        'view_url': view_url,
        'subject': subject,
        'basic_info': 'Report missing "Basic Information"'
    }

    data = get_report(report_id)
    for block in data['blocks']:
        if block['value']['name'].endswith('Basic Information'):
            info_data = {}
            for field in block['value']['fields']:
                if field['name'] == 'Starting run number':
                    info_data['start_run'] = field['value']
                if field['name'] == 'Ending run number':
                    info_data['end_run'] = field['value']
                if field['name'] == 'Crew':
                    info_data['crew'] = field['value']
                if field['name'] == 'Summary':
                    info_data['summary'] = field['value']
                if field['name'] == 'Synopsis':
                    info_data['synopsis'] = field['value']

            message_data['basic_info'] = \
'''Run number(s): %(start_run)s - %(end_run)s
Crew: %(crew)s
Summary: %(summary)s
Synopsis: %(synopsis)s
''' % info_data

            break

    message = \
'''%(subject)s

Report ID: %(id)s
Created: %(created)s
%(basic_info)s

View report: http://snopl.us%(view_url)s


This message was automatically generated by the Philadelphia shift report database.
''' % message_data

    email(settings.PHILA_EMAIL_LIST, subject, message)
    return HttpResponse(status=200)


@login_required
def timestamp(request):
    # Get formatted timestamp
    utctime = datetime.utcnow()
    if utctime.tzinfo is None:
        utctime = (pytz.timezone('UTC')).localize(utctime)

    # Get number of active run (if any)
    headers = make_headers(auth=settings.ORCADB_AUTH)
    url = '/orca/_design/snopldotus/_view/index?limit=1&descending=true&include_docs=true'
    run = 'no run active'
    try:
        data = json.loads(GET(settings.ORCADB_SERVER, url, headers))
        doc = data['rows'][0]
        run_id = doc['key']
        if doc['doc']['run_status'] == 'in progress':
            run = 'Run %i' % run_id
    except Exception:
        pass

    stamp = '[ %s (%s) ]' % (utctime.astimezone(tz).strftime(fmt), run)
    return HttpResponse(stamp)


@login_required
def whiteboard(request, doc_id):
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    if request.method == 'GET':
        conn, headers = make_db_connection()
        url = '/phila/%s' % doc_id
        conn.request('GET', url, headers=headers)
        response = conn.getresponse()
        doc = json.loads(response.read())
        doc['id'] = doc['_id']
        doc['rev'] = doc['_rev']

        utctime = dateutil.parser.parse(doc['saved'])
        if utctime.tzinfo is None:
            utctime = (pytz.timezone('UTC')).localize(utctime)
        doc['saved'] = utctime.astimezone(tz).strftime(fmt)

        if request.GET.get('json', False):
            return HttpResponse(json.dumps(doc), mimetype='application/json')

        doc['editor_id'] = uuid.uuid4().hex
        c = RequestContext(request, doc)
        t = loader.get_template('philadelphia/whiteboard.html')
        return HttpResponse(t.render(c))

    if request.method == 'POST':
        conn, headers = make_db_connection()
        url = '/phila/%s' % doc_id
        conn.request('GET', url, headers=headers)
        response = conn.getresponse()

        doc = json.loads(response.read())
        doc['text'] = request.POST['text']
        doc['saved'] = datetime.utcnow().isoformat()
        doc['revision'] = doc.get('revision', 0) + 1
        doc['editor_id'] = request.POST['editor_id']
        doc['title'] = request.POST['title']
        conn, headers = make_db_connection()
        url = '/phila/%s?rev=%s' % (doc_id, request.POST['_rev'])
        conn.request('PUT', url, json.dumps(doc), headers=headers)
        response = conn.getresponse()
        if not response.status < 400:
            return HttpResponse(status=response.status)

        d = json.loads(response.read())
        utctime = dateutil.parser.parse(doc['saved'])
        if utctime.tzinfo is None:
            utctime = (pytz.timezone('UTC')).localize(utctime)
        d['saved'] = utctime.astimezone(tz).strftime(fmt)

        return HttpResponse(json.dumps(d), mimetype='application/json')


@login_required
def whiteboards(request):
    '''Get a listing of whiteboards.

    :param request: Django request object
    :returns: HttpResponse
    '''
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    conn, headers = make_db_connection()
    url = '/phila/_design/phila/_view/boards'
    conn.request('GET', url, headers=headers)
    response = conn.getresponse()
    if not response.status < 400:
        return HttpResponse(status=response.status)

    boards = []
    data = json.loads(response.read())
    for row in data['rows']:
        d = row['value']
        d['id'] = row['key']
        d['id_short'] = d['id'][-8:]
        utctime = dateutil.parser.parse(d['created'])
        if utctime.tzinfo is None:
            utctime = (pytz.timezone('UTC')).localize(utctime)
        d['created'] = utctime.astimezone(tz).strftime(fmt)
        boards.append(d)

    boards = sorted(boards, key=lambda x: x['created'], reverse=True)

    t = loader.get_template('philadelphia/whiteboards.html')
    c = RequestContext(request, {'boards': boards})
    return HttpResponse(t.render(c))


@login_required
def new_whiteboard(request):
    '''Create a new whiteboard.

    This creates the DB documents and redirects to the editor.

    :param request: The Django request object
    :returns: (Temporary) redirect HttpResponse
    '''
    board_id = uuid.uuid4().hex

    board = {
        '_id': board_id,
        'type': 'board',
        'saved': datetime.utcnow().isoformat(),
        'text': '',
        'title': ''
    }

    url = '/phila/%s'
    conn, headers = make_db_connection()
    conn.request('PUT', url % board['_id'], json.dumps(board), headers=headers)
    response = conn.getresponse()
    if not response.status < 400:
        return HttpResponse(status=response.status)

    return redirect('/shift/whiteboard/%s' % board_id)

@login_required
def search(request, query=None):
    '''Perform a full-text search of the database, by field name.

    :param request: Django request object
    :param query: The query, as "field_name:query_text"
    :returns: HttpResponse
    '''
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()
    t = loader.get_template('philadelphia/search.html')

    if request.method == 'POST':
        field = request.POST.get('field')
        term = request.POST.get('term')
    else:
        term = query.split(':')
        if len(term) > 1:
            field, term = term
        else:
            field = None
            term = term[0]

    if field:
        qs = 'q=%s&include_docs=true&limit=10000' % ':'.join(map(quote, (field, term)))
        url = '/_fti/local/phila/_design/lucene/by_field?' + qs
    else:
        qs = 'q=%s&include_docs=true&limit=10000' % quote(term)
        url = '/_fti/local/phila/_design/lucene/everything?' + qs

    conn, headers = make_db_connection()
    conn.request('GET', url, headers=headers)
    response = conn.getresponse()

    if not response.status < 400:
        return HttpResponse(response.read(), status=response.status)

    def highlight(term, row, size=150):
        rows = []
        for m in re.finditer(term.lower(), row.lower()):
            s = ''
            if m.start() - size < 0:
                start = 0
            else:
                start = m.start() - size
                s += '...'

            s += row[start:m.start()]
            s += '<b>' + row[m.start():m.end()] + '</b>'
            s += row[m.end():min(len(row), m.end() + size)]

            if m.end() + size >= len(row):
                end = len(row)
            else:
                end = m.end() + size
                s += '...'

            rows.append(s)
        return rows

    results = json.loads(response.read())

    def norm_date(s):
        tz = pytz.timezone(settings.PHILA_TZ)
        fmt = '%Y/%m/%d %H:%M:%S (%Z)'
        utctime = dateutil.parser.parse(s, fuzzy=True)
        if utctime.tzinfo is None:
            utctime = (pytz.timezone('UTC')).localize(utctime)
        return utctime.astimezone(tz).strftime(fmt)

    results['rows'] = sorted(results['rows'],
                             key=lambda x: norm_date(x['doc']['created']),
                             reverse=True)

    if field:
        for i in range(len(results['rows'])):
            for j in results['rows'][i]['fields']:
              try:
                results['rows'][i]['fields'][j] = \
                  highlight(term, results['rows'][i]['fields'][j])
              except AttributeError:
                  return HttpResponse('<h1>400! Oh no!</h1>' + json.dumps(results['rows'][i]), content_type='application/json')
    else:
        for i in range(len(results['rows'])):
            for j in results['rows'][i]['fields']:
                o = results['rows'][i]['fields'][j]
                if not isinstance(o, list):
                    results['rows'][i]['fields'][j] = [o]
                results['rows'][i]['fields']['default'] = \
                    map(lambda x: highlight(term, x),
                        filter(lambda x: term in x,
                               results['rows'][i]['fields']['default']))
                if isinstance(results['rows'][i]['fields']['default'], list) and len(results['rows'][i]['fields']['default']) > 0:
                    results['rows'][i]['fields']['default'] = \
                        results['rows'][i]['fields']['default'][0]


    c = RequestContext(request, {
        'results': results,
        'field': field,
        'term': term,
        'method': request.method
    })
    return HttpResponse(t.render(c))

@login_required
def block_names(request):
    conn, headers = make_db_connection()
    url = '/phila/_design/phila/_view/keylist?group=true'
    conn.request('GET', url, headers=headers)
    response = conn.getresponse()
    if not response.status < 400:
        return HttpResponse(status=response.status)
    
    results = json.loads(response.read())
    names = [x['key'] for x in results['rows']]

    return HttpResponse(json.dumps(names))

