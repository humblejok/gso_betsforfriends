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
    url(r'^group_join.html$', 'bets.views.group_join', name='group_join'),
    url(r'^group_view.html$', 'bets.views.group_view', name='group_view'),
    
    url(r'^match_edit.html$', 'bets.views.match_edit', name='match_edit'),
    
    url(r'^save_bets.html$', 'bets.views.save_bets', name='save_bets'),
    
    url(r'^$', 'bets.views.index', name='index'),
)
