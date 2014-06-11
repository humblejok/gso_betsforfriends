from django.contrib import admin
from bets.models import Score, Match, Group, BettableEvent, EventRanking,\
    UserRanking

admin.site.register(BettableEvent)
admin.site.register(EventRanking)
admin.site.register(UserRanking)
admin.site.register(Group)
admin.site.register(Match)
admin.site.register(Score)