from django.contrib import admin
from bets.models import Score, Match, Group

admin.site.register(Group)
admin.site.register(Match)
admin.site.register(Score)