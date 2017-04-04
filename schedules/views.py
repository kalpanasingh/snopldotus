from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required

from schedules.models import Schedule
from schedules.forms import ScheduleForm

import hashlib

@login_required
def list(request):
    '''List and upload schedules.

    Thanks to http://stackoverflow.com/questions/5871730.
    '''
    request.user.gravatar_hash = \
        hashlib.md5(request.user.email.strip().lower()).hexdigest()

    # Handle file upload
    if request.method == 'POST':
        form = ScheduleForm(request.POST, request.FILES)
        if form.is_valid():
            newdoc = Schedule(
                docfile = request.FILES['docfile'],
                start_date = request.POST['start_date'],
                end_date = request.POST['end_date'],
                notes = request.POST['notes']
            )
            newdoc.save()

            # Redirect to the document list after POST
            return HttpResponseRedirect(reverse('schedules.views.list'))
    else:
        form = ScheduleForm()

    # Load documents for the list page
    schedules = reversed(Schedule.objects.all())

    # Render list page with the schedules and the form
    return render_to_response(
        'schedules/list.html', {
            'schedules': schedules,
            'form': form
        },
        context_instance=RequestContext(request)
    )

