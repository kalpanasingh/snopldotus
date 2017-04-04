from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'philadelphia.views.index'),
    url(r'^view/([a-fA-F0-9].+)$', 'philadelphia.views.report'),
    url(r'^delete/([a-fA-F0-9].+)$', 'philadelphia.views.delete'),
    url(r'^submit/([a-fA-F0-9].+)$', 'philadelphia.views.submit'),
    url(r'^save/?$', 'philadelphia.views.save'),
    url(r'^pdf/([a-fA-F0-9].+)$', 'philadelphia.views.pdf'),
    url(r'^search/(.+)$', 'philadelphia.views.search'),
    url(r'^search/$', 'philadelphia.views.search'),

    url(r'^attachment/$', 'philadelphia.views.attachment'),
    url(r'^attachment/([a-fA-F0-9].+)/(.+)$', 'philadelphia.views.attachment'),
    url(r'^delete-attachment/([a-fA-F0-9].+)$', 'philadelphia.views.attachment_delete'),

    url(r'^comment/([a-fA-F0-9].+)/([0-9].+)$', 'philadelphia.views.comment'),
    url(r'^comment/([a-fA-F0-9].+)/([0-9].+)?$', 'philadelphia.views.comment'),

    url(r'^new/?$', 'philadelphia.views.new'),
    url(r'^edit/([a-fA-F0-9].+)?$', 'philadelphia.views.edit'),
    url(r'^block/?([a-fA-F0-9].+)?$', 'philadelphia.views.block'),
    url(r'^timestamp/$', 'philadelphia.views.timestamp'),
    url(r'^block-names/$', 'philadelphia.views.block_names'),

    url(r'^whiteboards/?$', 'philadelphia.views.whiteboards'),
    url(r'^whiteboard/new/?$', 'philadelphia.views.new_whiteboard'),
    url(r'^whiteboard/?([a-fA-F0-9].+)?$', 'philadelphia.views.whiteboard'),

    # Shift schedules from the schedules app
    url(r'^schedules/$', 'schedules.views.list'),
)

