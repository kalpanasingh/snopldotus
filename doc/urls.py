from django.conf.urls import patterns, include, url
from django.views.generic.base import RedirectView

urlpatterns = patterns('',
    url(r'^rat/doxygen$', RedirectView.as_view(url='doxygen/', permanent=False)),
    url(r'^rat/doxygen(.+)$', 'doc.views.ratdox'),
    url(r'^rat/tasks$', 'doc.views.rat_tasks'),
    url(r'^rat(.+)$', 'doc.views.rat'),
)

