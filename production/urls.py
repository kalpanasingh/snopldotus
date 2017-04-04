from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^benchmarking/results', 'production.views.benchmarking_results'),
    url(r'^benchmarking/request$', 'production.views.benchmarking_request'),
    url(r'^production/request$', 'production.views.production_request'),
)

