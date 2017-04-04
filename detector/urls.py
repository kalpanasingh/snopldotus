from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'detector.views.overview', name='overview'),
    url(r'^update-subsystem', 'detector.views.update_subsystem'),
    url(r'^add-subsystem-tag', 'detector.views.add_subsystem_tag'),
)

