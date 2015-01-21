from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

import hello.views
import api.views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'hello.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^$', hello.views.index, name='index'),
    url(r'^api/upload$', api.views.uploadToS3Page, name='uploadToS3Page'),
    url(r'^api/upload-form$', api.views.uploadToS3Form, name='uploadToS3Form'),
    url(r'^api/process$', api.views.processReplayThatWasUploadedToS3, name='uploadToS3Form'),
    url(r'^api/result$', api.views.getProcessedReplayResult, name='getProcessedReplayResult'),
    url(r'^api-debug$', api.views.debug, name='apiDebugIndex'),
    url(r'^api-debug/result$', api.views.getProcessedReplayResult, name='getProcessedReplayResult'),


)
