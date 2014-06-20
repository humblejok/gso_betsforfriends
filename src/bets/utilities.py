# coding=utf-8
'''
Created on 18 juin 2014

@author: humble_jok
'''
from pymongo.mongo_client import MongoClient
from bets.models import Match, Attributes, Participant
from datetime import datetime as dt
from django.db.models import Q
from seq_common.utils import dates

MONGO_URL = 'mongodb://localhost:27017/'

client = MongoClient(MONGO_URL)

MATCHS_PER_TYPE = { 'MATCH_SIXTEENTH': 16,
                    'MATCH_EIGHTH': 8,
                    'MATCH_QUARTER': 4,
                    'MATCH_SEMIFINAL': 2,
                    'MATCH_FINAL': 1
                   }

def get_event_meta(event):
    return client['bets']['events'].find_one({'_id': event.id})

def set_event_meta(event, event_meta):
    client['bets']['events'].remove({'_id': event.id})
    client['bets']['events'].insert(event_meta)

def feed_fifa_wc2014():
    database = client['bets']
    event_meta = { 'final_phases' : ['MATCH_EIGHTH', 'MATCH_QUARTER', 'MATCH_SEMIFINAL', 'MATCH_FINAL'],
                   'groups_list' : ['A','B','C','D','E','F','G','H'],
                   'groups': { 'A': [{'id': 450, 'name':"Brazil"}, {'id': 467, 'name':"Mexico"}, {'id': 451, 'name':"Cameroon"}, {'id': 456, 'name':"Croatia"}],
                               'B': [{'id': 468, 'name':"Netherlands"}, {'id': 452, 'name':"Chile"}, {'id': 447, 'name':"Australia"}, {'id': 473, 'name':"Spain"}],
                               'C': [{'id': 453, 'name':"Colombia"}, {'id': 455, 'name':"Côte d'Ivoire"}, {'id': 462, 'name':"Greece"}, {'id': 466, 'name':"Japan"}],
                               'D': [{'id': 454, 'name':"Costa Rica"}, {'id': 465, 'name':"Italy"}, {'id': 458, 'name':"England"}, {'id': 475, 'name':"Uruguay"}],
                               'E': [{'id': 459, 'name':"France"}, {'id': 457, 'name':"Ecuador"}, {'id': 474, 'name':"Switzerland"}, {'id': 463, 'name':"Honduras"}, ],
                               'F': [{'id': 449, 'name':"Bosnia and Herzegovina"}, {'id': 446, 'name':"Argentina"}, {'id': 464, 'name':"Iran"}, {'id': 469, 'name':"Nigeria"}],
                               'G': [{'id': 470, 'name':"Portugal"}, {'id': 460, 'name':"Germany"}, {'id': 476, 'name':"USA"}, {'id': 461, 'name':"Ghana"}],
                               'H': [{'id': 445, 'name':"Algeria"}, {'id': 448, 'name':"Belgium"}, {'id': 471, 'name':"Russia"}, {'id': 472, 'name':"South Korea"}]
                              },
                    '_id': 525
                  }
    database['events'].remove({'_id': 525})
    database['events'].insert(event_meta)

def search_in(dicts, _id):
    values = [e for e in dicts if e['id']==_id]
    if len(values)==0:
        return None
    else:
        return values[0]
    

def compute_fifa_wc_pools(event):
    event_meta = get_event_meta(event)
    pool_matchs = {}
    for group_id in event_meta['groups']:
        group = event_meta['groups'][group_id]
        for participant in group:
            participant['goals'] = 0
            participant['points'] = 0
    for group_id in event_meta['groups']:
        group = event_meta['groups'][group_id]
        matchs = []
        for i in range(0, len(group) - 1):
            for j in range(i + 1, len(group)):
                effective_match = event.matchs.filter(Q(type__identifier='MATCH_POOL'),Q(first__id=group[i]['id']) | Q(second__id=group[i]['id']), Q(first__id=group[j]['id']) | Q(second__id=group[j]['id']))
                effective_match = effective_match[0]
                match_details = {'first' : {'id': effective_match.first.id, 'name': effective_match.first.name},
                                 'second': {'id': effective_match.second.id, 'name': effective_match.second.name},
                                 'id': effective_match.id
                                }
                if effective_match.result!=None:
                    match_details['score'] = {'first':effective_match.result.first, 'second':effective_match.result.second,
                                              'winner': None if effective_match.result.first==effective_match.result.second
                                                    else {'id': effective_match.first.id, 'name': effective_match.first.name} if effective_match.result.first>effective_match.result.second
                                                    else {'id': effective_match.second.id, 'name': effective_match.second.name}}
                    search_in(group, effective_match.first.id)['goals'] += effective_match.result.first
                    search_in(group, effective_match.second.id)['goals'] += effective_match.result.second
                    winner = effective_match.get_winner()
                    if winner==None:
                        search_in(group, effective_match.first.id)['points'] += 1
                        search_in(group, effective_match.second.id)['points'] += 1
                    else:
                        if winner.id==effective_match.first.id:
                            search_in(group, effective_match.first.id)['points'] += 3
                            search_in(group, effective_match.second.id)['points'] += 0
                        else:
                            search_in(group, effective_match.first.id)['points'] += 0
                            search_in(group, effective_match.second.id)['points'] += 3
                matchs.append(match_details)
        # Sorting pools participants
        event_meta['groups'][group_id] = sorted(group, key=lambda x: (x["points"],x['goals']), reverse=True)
        # Assigning matches        
        pool_matchs[group_id] = matchs
        
    event_meta['pool_matchs'] = pool_matchs
    set_event_meta(event, event_meta)
    
def compute_fifa_wc_8th(event):
    for match in event.matchs.filter(type__identifier='MATCH_EIGHTH'):
        event.matchs.remove(match)
        match.delete()
    event.save()    
    
    event_meta = get_event_meta(event)
    
    for index in range(0,4):
        effective_match = Match()
        first = event_meta['groups'][event_meta['groups_list'][index * 2]][0]
        second = event_meta['groups'][event_meta['groups_list'][(index * 2) + 1]][1]
        effective_match.name = first['name'] + ' vs ' + second['name'] + ' [1' + event_meta['groups_list'][index * 2] + ' - 2' + event_meta['groups_list'][(index * 2) + 1] + ']'
        effective_match.type = Attributes.objects.get(identifier='MATCH_EIGHTH', type='match_type')
        effective_match.when = dt.combine(dates.AddDay(event.start_date,16 + index) , dt.min.time())
        effective_match.first = Participant.objects.get(id=first['id'])
        effective_match.second = Participant.objects.get(id=second['id'])
        effective_match.save()
        event.matchs.add(effective_match)
        event.save()
        effective_match = Match()
        first = event_meta['groups'][event_meta['groups_list'][(index * 2) + 1]][0]
        second = event_meta['groups'][event_meta['groups_list'][index * 2]][1]
        effective_match.name = first['name'] + ' vs ' + second['name'] + ' [1' + event_meta['groups_list'][(index * 2) + 1] + ' - 2' + event_meta['groups_list'][index * 2] + ']'
        effective_match.type = Attributes.objects.get(identifier='MATCH_EIGHTH', type='match_type')
        effective_match.when = dt.combine(dates.AddDay(event.start_date,16 + index) , dt.min.time())
        effective_match.first = Participant.objects.get(id=first['id'])
        effective_match.second = Participant.objects.get(id=second['id'])
        effective_match.save()
        event.matchs.add(effective_match)
        event.save()
    complete_fifa_wc(event,'MATCH_EIGHTH')

def complete_fifa_wc(event, match_type):
    event_meta = get_event_meta(event)
    event_meta[match_type] = []
    all_matchs = event.matchs.filter(type__identifier='MATCH_EIGHTH').order_by('when')
    for match in all_matchs:
        match_details = {'first' : {'id': match.first.id, 'name': match.first.name},
                         'second': {'id': match.second.id, 'name': match.second.name},
                         'id': match.id
                }
        if match.result!=None:
            match_details['score'] = {'first':match.result.first, 'second':match.result.second,
                                      'winner': None if match.result.first==match.result.second
                                                else {'id': match.first.id, 'name': match.first.name} if match.result.first>match.result.second
                                                else {'id': match.second.id, 'name': match.second.name}}
        event_meta[match_type].append(match_details)
    if not all_matchs.exists():
        for i in MATCHS_PER_TYPE[match_type]:
            match_details = {'first' : {'id': None, 'name': None},
                     'second': {'id': None, 'name': None},
                     'id': None
            }
        event_meta[match_type].append(match_details)
    set_event_meta(event, event_meta)
    
def compute_fifa_wc_table(event):
    event_meta = get_event_meta(event)
       
    set_event_meta(event, event_meta)