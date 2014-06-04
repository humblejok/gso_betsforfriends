from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # DJango default views
    url(r'^accounts/', include('allauth.urls')),
    url(r'^admin/', include(admin.site.urls)),
    # Main page
    url(r'^index.html$', 'bets.views.index', name='index'),
    url(r'^group_create.html$', 'bets.views.group_create', name='group_create'),
    
)
