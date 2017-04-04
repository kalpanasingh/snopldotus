from django.http import HttpResponse
from django.shortcuts import redirect
from django.template import RequestContext, Context, loader
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from snopldotus.models import UserProfile

import os
import md5
import mimetypes
import requests

RAT_DOC_ROOT = '/data/docbuild/rat/doc'
RAT_DOX_ROOT = '/data/doxbuild/rat/dox/html'

@login_required
def rat(request, path):
    request.user.gravatar_hash = md5.md5(request.user.email.strip().lower()).hexdigest()

    if not path or path == '' or path == '/':
        path = '/index.html'

    with open(os.path.join(RAT_DOC_ROOT, path.lstrip('/')), 'rb') as f:
        content = f.read()

    if not path.endswith('.html'):
        mime = mimetypes.guess_type(f.name)
        return HttpResponse(content, mimetype=mime)

    t = loader.get_template('doc/rat.html')
    c = RequestContext(request, {
        'content': content
    })
    return HttpResponse(t.render(c))


@login_required
def ratdox(request, path):
    request.user.gravatar_hash = md5.md5(request.user.email.strip().lower()).hexdigest()

    if not path or path == '' or path == '/' or path == 'doxygen':
        path = '/index.html'

    with open(os.path.join(RAT_DOX_ROOT, path.lstrip('/')), 'rb') as f:
        content = f.read()

    if path.endswith('.css'):
        return HttpResponse(content, mimetype='text/css')

    if not path.endswith('.html'):
        mime = mimetypes.guess_type(f.name)
        return HttpResponse(content, mimetype=mime)

    t = loader.get_template('doc/rat.html')
    c = RequestContext(request, {
        'content': content
    })
    return HttpResponse(t.render(c))


@login_required
def rat_tasks(request):
    '''Nuno's RAT tasks page.'''
    request.user.gravatar_hash = md5.md5(request.user.email.strip().lower()).hexdigest()

    req = requests.get('http://www.hep.upenn.edu/~nfbarros/RAT/index.html')
    content = req.text

    t = loader.get_template('doc/rat_tasks.html')
    c = RequestContext(request, {
        'content': content
    })
    return HttpResponse(t.render(c))

