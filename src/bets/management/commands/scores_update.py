'''
Created on 15 juin 2014

@author: humble_jok
'''
from django.core.management.base import BaseCommand
from datetime import datetime as dt
import datetime
from seq_common.utils import dates
from bets.models import BettableEvent, Provider, generate_matchs,\
    compute_event_ranking, compute_group_ranking, compute_overall_ranking
from bets.utilities import get_event_meta, complete_meta_for_type

class Command(BaseCommand):
    help = 'For all available providers and current events, it updates the scores'
    
    def handle(self, *args, **options):
        begin = dt.combine(dates.AddDay(datetime.date.today(),-7), dt.min.time())
        active_events = BettableEvent.objects.filter(end_date__gte=begin).order_by('name')
        for event in active_events:
            providers = Provider.objects.filter(event__id=event.id)
            event_meta = get_event_meta(event)
            for provider in providers:
                provider.get_all_matches_info()
            for m_type in event_meta['final_phases'][1:]:
                complete_meta_for_type(event, m_type)
        compute_event_ranking()
        compute_group_ranking()
        compute_overall_ranking()
        generate_matchs()