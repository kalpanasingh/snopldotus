from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'waterlevel.views.index'),
    url(r'^level.json$', 'waterlevel.views.json_level'),
)

