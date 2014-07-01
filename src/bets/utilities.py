# coding=utf-8
'''
Created on 18 juin 2014

@author: humble_jok
'''
from pymongo.mongo_client import MongoClient
from bets.models import Match, Attributes, Participant, Group, UserRanking,\
    EventRanking, Bet, WinnerSetup, Winner, rank_list, PointsSetup, Score
from datetime import datetime as dt
from django.db.models import Q
from seq_common.utils import dates
import datetime
import logging

LOGGER = logging.getLogger(__name__)

MONGO_URL = 'mongodb://localhost:27017/'

client = MongoClient(MONGO_URL)

MATCHS_PER_TYPE = { 'MATCH_SIXTEENTH': 16,
                    'MATCH_EIGHTH': 8,
                    'MATCH_QUARTER': 4,
                    'MATCH_SEMIFINAL': 2,
                    'MATCH_FINAL': 1
                   }

POINTS_PER_TYPE = {
                    'MATCH_SIXTEENTH': [],
                    'MATCH_EIGHTH': [],
                    'MATCH_QUARTER': [0,0,0,0,4,6,8,10,12],
                    'MATCH_SEMIFINAL': [0,2,4,8,12],
                    'MATCH_FINAL': [0,6,12],
                    'MATCH_FINAL': [0,12]
                   }

def get_event_meta(event):
    return client['bets']['events'].find_one({'_id': event.id})

def set_event_meta(event, event_meta):
    client['bets']['events'].remove({'_id': event.id})
    client['bets']['events'].insert(event_meta)

def feed_wimbledon_2014():
    database = client['bets']
    event_meta = { 'matches_per_type': MATCHS_PER_TYPE,
                   'final_phases' : ['MATCH_EIGHTH', 'MATCH_QUARTER', 'MATCH_SEMIFINAL', 'MATCH_FINAL'],
                   'bets_delays' : {'MATCH_EIGHTH': 14, 'MATCH_QUARTER': 14, 'MATCH_SEMIFINAL': 21, 'MATCH_FINAL': 21, 'MATCH_WINNER': 21},
                   'groups_list' : [],
                   'groups': {},
                   '_id': 8651
                   }
    database['events'].remove({'_id': 8651})
    database['events'].insert(event_meta)
    database = client['bets']
    event_meta = { 'matches_per_type': MATCHS_PER_TYPE,
                   'final_phases' : ['MATCH_EIGHTH', 'MATCH_QUARTER', 'MATCH_SEMIFINAL', 'MATCH_FINAL'],
                   'bets_delays' : {'MATCH_EIGHTH': 1, 'MATCH_QUARTER': 7, 'MATCH_SEMIFINAL': 7, 'MATCH_FINAL': 7, 'MATCH_WINNER': 7},
                   'groups_list' : [],
                   'groups': {},
                   '_id': 8652
                   }
    database['events'].remove({'_id': 8652})
    database['events'].insert(event_meta)

def feed_fifa_wc2014():
    database = client['bets']
    event_meta = { 'matches_per_type': MATCHS_PER_TYPE,
                   'final_phases' : ['MATCH_EIGHTH', 'MATCH_QUARTER', 'MATCH_SEMIFINAL', 'MATCH_FINAL'],
                   'bets_delays' : {'MATCH_EIGHTH': 7, 'MATCH_QUARTER': 21, 'MATCH_SEMIFINAL': 21, 'MATCH_FINAL': 21, 'MATCH_WINNER': 21},
                   'groups_list' : ['A','B','C','D','E','F','G','H'],
                   'groups': { 'A': [{'id': 450, 'name':"Brazil",'quote': 4.25}, {'id': 467, 'name':"Mexico",'quote': 60.0}, {'id': 451, 'name':"Cameroon",'quote': 0.0}, {'id': 456, 'name':"Croatia",'quote': 100.0}],
                               'B': [{'id': 468, 'name':"Netherlands",'quote': 10.0}, {'id': 452, 'name':"Chile",'quote': 15.0}, {'id': 447, 'name':"Australia",'quote': 0.0}, {'id': 473, 'name':"Spain",'quote': 0.0}],
                               'C': [{'id': 453, 'name':"Colombia",'quote': 20.0}, {'id': 455, 'name':"Côte d'Ivoire",'quote': 100.0}, {'id': 462, 'name':"Greece",'quote': 500.0}, {'id': 466, 'name':"Japan",'quote': 501.0}],
                               'D': [{'id': 454, 'name':"Costa Rica",'quote': 60.0}, {'id': 465, 'name':"Italy",'quote': 20.0}, {'id': 458, 'name':"England",'quote': 0.0}, {'id': 475, 'name':"Uruguay",'quote': 40.0}],
                               'E': [{'id': 459, 'name':"France",'quote': 7.5}, {'id': 457, 'name':"Ecuador", 'quote': 301.0}, {'id': 474, 'name':"Switzerland",'quote': 150.0}, {'id': 463, 'name':"Honduras",'quote': 2501.0} ],
                               'F': [{'id': 449, 'name':"Bosnia and Herzegovina",'quote': 0.0}, {'id': 446, 'name':"Argentina",'quote': 4.75}, {'id': 464, 'name':"Iran",'quote': 500.0}, {'id': 469, 'name':"Nigeria",'quote': 150.0}],
                               'G': [{'id': 470, 'name':"Portugal",'quote': 35.0}, {'id': 460, 'name':"Germany",'quote': 4.50}, {'id': 476, 'name':"USA",'quote': 150.0}, {'id': 461, 'name':"Ghana",'quote': 251.0}],
                               'H': [{'id': 445, 'name':"Algeria",'quote': 0.0}, {'id': 448, 'name':"Belgium",'quote': 18.0}, {'id': 471, 'name':"Russia",'quote': 150.0}, {'id': 472, 'name':"South Korea",'quote': 500.0}]
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
    
def generates_per_participant_result(event):
    event_meta = get_event_meta(event)
    participants_matchs = {}
    for match in event.matchs.filter(result__isnull=False).order_by('when'):
        if not participants_matchs.has_key(str(match.first.id)):
            participants_matchs[str(match.first.id)] = []
        if not participants_matchs.has_key(str(match.second.id)):
            participants_matchs[str(match.second.id)] = []
        participants_matchs[str(match.first.id)].append({'first':{'name':match.first.name, 'id':match.first.id, 'score': match.result.first}, 'second':{'name':match.second.name, 'id':match.second.id, 'score': match.result.second}})
        participants_matchs[str(match.second.id)].append({'first':{'name':match.second.name, 'id':match.second.id, 'score': match.result.second}, 'second':{'name':match.first.name, 'id':match.first.id, 'score': match.result.first}})
    event_meta['participants_matchs'] = participants_matchs
    set_event_meta(event, event_meta)
            
    

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
    if (datetime.date.today()-event.start_date).days<15:
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
        complete_meta_for_type(event,'MATCH_EIGHTH')

def complete_any_event(event, match_type):
    event_meta = get_event_meta(event)
    event_meta[match_type] = []
    all_matchs = event.matchs.filter(type__identifier=match_type).order_by('when')
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
        for i in range(0,MATCHS_PER_TYPE[match_type]):
            match_details = {'first' : {'id': None, 'name': None},
                     'second': {'id': None, 'name': None},
                     'id': None
            }
            event_meta[match_type].append(match_details)
    set_event_meta(event, event_meta)

def complete_meta_for_type(event, match_type):
    event_meta = get_event_meta(event)
    event_meta[match_type] = {'teams': [], 'matchs':[]}
    all_matchs = event.matchs.filter(type__identifier=match_type).order_by('when')
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
        event_meta[match_type]['matchs'].append(match_details)
        event_meta[match_type]['teams'].append({'id': match.first.id, 'name': match.first.name})
        event_meta[match_type]['teams'].append({'id': match.second.id, 'name': match.second.name})
    if not all_matchs.exists():
        for i in range(0,MATCHS_PER_TYPE[match_type]):
            match_details = {'first' : {'id': None, 'name': None},
                     'second': {'id': None, 'name': None},
                     'id': None
            }
            event_meta[match_type]['matchs'].append(match_details)
    set_event_meta(event, event_meta)
    
def compute_group_ranking(group_id=None):
    today = dates.AddDay(datetime.date.today(),-1)
    if group_id==None:
        all_groups = Group.objects.filter(event__end_date__gte=today)
    else:
        all_groups = Group.objects.filter(id=group_id)
    for group in all_groups:
        ranks = []
        if not group.owners.all()[0].groups.filter(name='allow_amount').exists():
            LOGGER.info("Working on group " + str(group.name))
            for user in list(group.members.all()) + list(group.owners.all()):
                LOGGER.info("\tWorking on user " + str(user.username))
                ranking = UserRanking.objects.filter(owner__id=user.id, group__id=group.id)
                if not ranking.exists():
                    ranking = UserRanking()
                    ranking.owner = user
                    ranking.group = group
                    ranking.overall_score = 0
                    ranking.rank = None
                    ranking.save()
                else:
                    ranking = ranking[0]
                ranks.append(ranking)
                event_rank = EventRanking.objects.filter(event__id=group.event.id, owner__id=user.id)
                if event_rank.exists():
                    event_rank = event_rank[0]
                    ranking.overall_score = event_rank.overall_score
                    ranking.save()
                else:
                    LOGGER.warn("User [" + str(user.id) +"] has no rank in event:" + str(group.event.name))
        else:
            LOGGER.info("Working on group with event and amount: " + unicode(group.event.name))
            events_ranking = {}
            for user in list(group.members.all()) + list(group.owners.all()):
                LOGGER.info("\tWorking on user " + unicode(user.username))
                for match in group.event.matchs.filter(result__isnull=False):
                    LOGGER.info("\t\tWorking on match " + unicode(match.name))
                    bet = Bet.objects.filter(match__id=match.id, owner__id=user.id)
                    winner = match.get_winner()
                    LOGGER.info("\t\tWinner is " + unicode(winner))
                    if bet.exists():
                        bet = bet[0]
                        if bet.amount!=None and bet.amount!=0:
                            score = bet.get_score()
                            if not events_ranking.has_key(group.event.id):
                                events_ranking[group.event.id] = {}
                            if not events_ranking[group.event.id].has_key(user.id):
                                rank = EventRanking()
                                rank.event = group.event
                                rank.owner = user
                                rank.overall_score = 0
                                rank.rank = None
                                events_ranking[group.event.id][user.id] = rank
                                LOGGER.info("\t\tResult: FINAL CREATION = " + str(events_ranking[group.event.id][user.id].overall_score))
                            events_ranking[group.event.id][user.id].overall_score += score
                            LOGGER.info("\t\tResult: FINAL score = " + str(events_ranking[group.event.id][user.id].overall_score))
                ranking = UserRanking.objects.filter(owner__id=user.id, group__id=group.id)
                if not ranking.exists():
                    ranking = UserRanking()
                    ranking.owner = user
                    ranking.group = group
                    ranking.overall_score = 0
                    ranking.rank = None
                    ranking.save()
                else:
                    ranking = ranking[0]
                if events_ranking[group.event.id].has_key(user.id):
                    ranking.overall_score = events_ranking[group.event.id][user.id].overall_score
                else:
                    ranking.overall_score = 0                    
                ranking.save()
                ranks.append(ranking)
        winner_setups = WinnerSetup.objects.filter(group__id=group.id)
        event_meta = get_event_meta(group.event)
        rank_list(ranks)
        ranks = []
        for a_setup in winner_setups:
            for per_type in a_setup.setup.all():
                LOGGER.info("Adding winner bets results for " + per_type.category.identifier)
                if per_type.category.identifier!='MATCH_WINNER':
                    data = [team['id'] for team in event_meta[per_type.category.identifier]['teams']]
                else:
                    last_match = group.event.matchs.filter(result__isnull=False, type__identifier='MATCH_WINNER')
                    if last_match.exists():
                        data = [last_match.first.id if last_match.result.first>last_match.result.second else last_match.second.id]
                    else:
                        data = []
                print data
                for user in list(group.members.all()) + list(group.owners.all()):
                    winner = Winner.objects.filter(owner__id=user.id, event__id=group.event.id, category__identifier=per_type.category.identifier)
                    if winner.exists():
                        winner = winner[0]
                        found = len(winner.participants.filter(id__in=data))
                        ranking = UserRanking.objects.get(owner__id=user.id, group__id=group.id)
                        if per_type.use_quotes:
                            LOGGER.info("User " + user.username + " found " + str(found) + " teams, adding " + str(found * per_type.points) + " points")
                            ranking.overall_score = ranking.overall_score + (found * per_type.points)
                        else:
                            LOGGER.info("User " + user.username + " found " + str(found) + " teams, adding " + str(POINTS_PER_TYPE[per_type.category.identifier][found]) + " points")
                            ranking.overall_score = ranking.overall_score + POINTS_PER_TYPE[per_type.category.identifier][found]
                        ranking.save()
                    ranks.append(ranking)
        rank_list(ranks)