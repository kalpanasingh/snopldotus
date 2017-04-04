from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^$', 'debugdb.views.index'),
    url(r'^boards$', 'debugdb.views.boards'),
    url(r'^spares$', 'debugdb.views.spares'),
    url(r'^board/(?P<board_id>[a-zA-Z0-9].+)/tests$', 'debugdb.views.tests', {'name': None}),
    url(r'^board/([a-zA-Z0-9].+)$', 'debugdb.views.board'),
    url(r'^tests/(?P<name>[a-zA-Z0-9].+)$', 'debugdb.views.tests', {'board_id': None}),
    url(r'^tests$', 'debugdb.views.tests', {'board_id': None, 'name': None}),
    url(r'^test/([a-zA-Z0-9].+)$', 'debugdb.views.test'),
    url(r'^test-names$', 'debugdb.views.test_names'),
    url(r'^crate/([0-9]{1,2})$', 'debugdb.views.crate'),
    url(r'^ecals$', 'debugdb.views.ecals', ),
    url(r'^ecal/([a-fA-F0-9].+)$', 'debugdb.views.ecal'),
    url(r'^detector$', 'debugdb.views.detector', ),
    url(r'^new-tag$', 'debugdb.views.new_tag', ),
    url(r'^fecdoc/([a-fA-F0-9].+)$', 'debugdb.views.fecdoc'),
    url(r'^reconfig$', 'debugdb.views.reconfig'),
)

