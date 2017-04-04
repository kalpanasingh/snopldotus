import os
import time
import hashlib
import json

from django.http import HttpResponse
from django.template import RequestContext, Context, loader
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import condition
from django.conf import settings
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

import external_model


@login_required
def index(request):
    '''Water level'''
    template = loader.get_template('waterlevel/index.html')
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    # Generate the plot if it does not exist or if it is older than one day
    image_path = os.path.join(settings.STATICFILES_DIRS[0], "images",
                              "generated", "waterlevel.png")
    tension_image_path = os.path.join(settings.STATICFILES_DIRS[0], "images",
                              "generated", "tension.png")

    now = time.time()
    if (not os.path.exists(image_path) or
        now - os.path.getmtime(image_path) > 3600):
            external_model.make_plot(image_path)
    if (not os.path.exists(tension_image_path) or
        now - os.path.getmtime(tension_image_path) > 3600):
            external_model.make_tension_plot(tension_image_path)


    current_level = list(external_model.get_current_waterlevel())
    if current_level[1] != 'N/A':
        current_level[2] *= 2.31  # Pi server conversion

    context = RequestContext(request, {
        'estimated_fill_enddate': external_model.get_enddate().__str__(),
        'current_level': current_level,
        'optimistic_fillrate': external_model.FEET_PER_SHIFT_OPT,
        'pessimistic_fillrate': external_model.FEET_PER_SHIFT_PES,
    })
    return HttpResponse(template.render(context))

@login_required
def json_level(request):
    '''Serve the current waterlevel as a JSON document'''
    return HttpResponse(json.dumps(external_model.get_current_waterlevel()[1]), content_type="application/json")
