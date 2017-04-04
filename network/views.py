from django.http import HttpResponse
from django.template import RequestContext, Context, loader
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import condition
from django.conf import settings
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

import hashlib
from nagios import get_hosts

@login_required
def status(request):
    '''View details for a particular run.'''
    t = loader.get_template('network/status.html')
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()
    nagios_hosts = get_hosts()

    nagios_hosts_sorted = sorted(nagios_hosts.items())

    c = RequestContext(request, {
        'nagios_hosts': nagios_hosts_sorted,
        'nagios_hosts_dict': nagios_hosts,
    })
    return HttpResponse(t.render(c))

