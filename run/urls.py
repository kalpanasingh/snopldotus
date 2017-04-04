from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'run.views.index'),
    url(r'^([0-9].+)$', 'run.views.run'),
)

