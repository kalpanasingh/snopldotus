from django.http import HttpResponse
from django.template import RequestContext, loader
from django.contrib.auth.decorators import login_required
from django.forms.models import modelform_factory

from snopldotus.xdr_registry import registry
from detector.models import Subsystem, Tag

import md5

@login_required
def overview(request):
    t = loader.get_template('detector/overview.html')
    request.user.gravatar_hash = md5.md5(request.user.email.strip().lower()).hexdigest()

    subsystems = Subsystem.objects.order_by('name')
    tag_form = modelform_factory(Tag)

    for system in subsystems:
        system.tags = Tag.objects.filter(subsystem=system).order_by('timestamp').reverse()

    context = {
        'subsystems': subsystems,
        'tag_form': tag_form
    }

    c = RequestContext(request, context)
    return HttpResponse(t.render(c))

@login_required
def update_subsystem(request):
    if request.method == 'POST':
        data = request.POST
        subsystem = Subsystem.objects.filter(name=data['subsystem'])[0]
        if data['field'] == 'problems':
            if data['value'] == 'true':
                subsystem.problems = False
            else:
                subsystem.problems = True
        elif data['field'] == 'enabled':
            if data['value'] == 'true':
                subsystem.enabled = True
            else:
                subsystem.enabled = False
        else:
            raise Exception('malformed query')

        subsystem.save()
        return HttpResponse('{"results": "ok"}',
                            content_type='application/json')


@login_required
def add_subsystem_tag(request):
    if request.method == 'POST':
        tag_form = modelform_factory(Tag)
        form = tag_form(request.POST, request.FILES)
        print form
        if form.is_valid():
            form.save()
            return HttpResponse('{"results": "ok"}',
                                content_type='application/json')
        else:
            raise Exception('malformed query')


@login_required
def websnoed(request):
    t = loader.get_template('detector/websnoed.html')
    request.user.gravatar_hash = md5.md5(request.user.email.strip().lower()).hexdigest()

    token = registry.register(request.user.username, 'websnoed')

    c = RequestContext(request, {
        'username': request.user.username,
        'xdr_token': token
    })
    return HttpResponse(t.render(c))

