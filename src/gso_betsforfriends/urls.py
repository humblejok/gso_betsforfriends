from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin

admin.autodiscover()

handler400 = 'bets.views.badrequest'
handler403 = 'bets.views.forbidden'

urlpatterns = patterns('',
    # DJango default views
    url(r'^accounts/', include('allauth.urls')),
    url(r'^admin/', include(admin.site.urls)),
    # Main page
    url(r'^index.html$', 'bets.views.index', name='index'),
    
    url(r'^event_view.html$', 'bets.views.event_view', name='event_view'),    
    
    url(r'^group_compare.html$', 'bets.views.group_compare', name='group_compare'),    
    url(r'^group_create.html$', 'bets.views.group_create', name='group_create'),
    url(r'^group_details.html$', 'bets.views.group_details', name='group_details'),
    
    url(r'^group_join.html$', 'bets.views.group_join', name='group_join'),
    url(r'^group_view.html$', 'bets.views.group_view', name='group_view'),
    url(r'^group_edit.html$', 'bets.views.group_edit', name='group_edit'),
    url(r'^group_remove_user.html$', 'bets.views.group_remove_user', name='group_remove_user'),
    url(r'^group_winner_bet.html$', 'bets.views.group_winner_bet', name='group_winner_bet'),
    url(r'^group_winner_bet_save.html$', 'bets.views.group_winner_bet_save', name='group_winner_bet_save'),
    
    
    url(r'^matchs_edit.html$', 'bets.views.matchs_edit', name='matchs_edit'),
    url(r'^matchs_save.html$', 'bets.views.matchs_save', name='matchs_save'),
    url(r'^matchs_compute.html$', 'bets.views.matchs_compute', name='matchs_compute'),
    url(r'^matchs_generate.html$', 'bets.views.matchs_generate', name='matchs_generate'),
    url(r'^matchs_schedule.html$', 'bets.views.matchs_schedule', name='matchs_schedule'),
    url(r'^matchs_schedule_update.html$', 'bets.views.matchs_schedule_update', name='matchs_schedule_update'),
    
    url(r'^profile_show.html$', 'bets.views.profile_show', name='profile_show'),
    
    url(r'^bets_save.html$', 'bets.views.bets_save', name='bets_save'),
    url(r'^bets_winner_save.html$', 'bets.views.bets_winner_save', name='bets_winner_save'),
    
    
    
    url(r'^$', 'bets.views.index', name='home'),
)
