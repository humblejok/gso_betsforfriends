from django.contrib import admin
from bets.models import Score, Match, Group, BettableEvent, EventRanking,\
    UserRanking, Provider, ProviderMapping, Winner, WinnerSetup

admin.site.register(BettableEvent)
admin.site.register(EventRanking)
admin.site.register(UserRanking)
admin.site.register(Winner)
admin.site.register(WinnerSetup)
admin.site.register(Provider)
admin.site.register(ProviderMapping)
admin.site.register(Group)
admin.site.register(Match)
admin.site.register(Score)