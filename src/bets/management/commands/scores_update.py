'''
Created on 15 juin 2014

@author: humble_jok
'''
from django.core.management.base import BaseCommand
from datetime import datetime as dt
import datetime
from seq_common.utils import dates
from bets.models import BettableEvent, Provider

class Command(BaseCommand):
    help = 'For all available providers and current events, it updates the scores'
    
    def handle(self, *args, **options):
        begin = dt.combine(dates.AddDay(datetime.date.today(),-7), dt.min.time())
        active_events = BettableEvent.objects.filter(end_date__gte=begin).order_by('name')
        for event in active_events:
            providers = Provider.objects.filter(event__id=event.id)
            for provider in providers:
                provider.get_all_matches_info()
        