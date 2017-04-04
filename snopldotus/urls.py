from django.conf.urls import patterns, include, url
from django.contrib import admin
admin.autodiscover()

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = patterns('',
    # Index
    url(r'^$', 'snopldotus.views.index', name='index'),

    # Collaboration and users
    url(r'^collaboration/people', 'snopldotus.views.collaboration_list'),
    url(r'^calls', 'snopldotus.views.calls'),
    url(r'^oncall', 'snopldotus.views.oncall'),
    url(r'^phonelist', 'snopldotus.views.phone_list'),
    url(r'^user/([a-zA-Z]+)$', 'snopldotus.views.user'),

    # Code
    url(r'^code/build$', 'snopldotus.views.build_tests', {'db': 'production'}),
    url(r'^code/build/record/([a-zA-Z0-9]+)$', 'snopldotus.views.build_test', {'db': 'production'}),
    url(r'^code/build/task/(\w+)$', 'snopldotus.views.build_task', {'db': 'production'}),
    url(r'^code/ondemand$', 'snopldotus.views.build_tests', {'db': 'ondemand'}),
    url(r'^code/ondemand-dev$', 'snopldotus.views.btdev', {'db': 'ondemand'}),
    url(r'^code/ondemand/record/([a-zA-Z0-9]+)$', 'snopldotus.views.build_test', {'db': 'ondemand'}),
    url(r'^code/ondemand/task/(\w+)$', 'snopldotus.views.build_task', {'db': 'ondemand'}),
    url(r'^code/([a-zA-Z0-9|-]+)/attachment/([a-zA-Z0-9]+)/(.+)$', 'snopldotus.views.build_attachment'),

    # DB replications
    url(r'^dbstatus$', 'snopldotus.views.db_replication_status'),
    url(r'^kick-replications/(.+)$', 'snopldotus.views.restart_replications'),

    # Apps
    #url(r'^detector/', include('detector.urls')),
    url(r'^shift/', include('philadelphia.urls')),
    url(r'^docs/', include('doc.urls')),
    url(r'^runs/', include('run.urls')),
    url(r'^waterlevel/', include('waterlevel.urls')),
    url(r'^debugdb/', include('debugdb.urls')),
    url(r'^network/', include('network.urls')),
    url(r'^production/', include('production.urls')),

    # Utilities
    url(r'^login$', 'django.contrib.auth.views.login', {'template_name': 'snopl.us/login.html'}),
    url(r'^validate$', 'snopldotus.views.xdr_validate'),
    url(r'^logout', 'snopldotus.views.logout_view'),
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()

