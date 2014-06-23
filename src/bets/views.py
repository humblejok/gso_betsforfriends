from django.db.models import Q
from django.shortcuts import render, redirect

from bets.models import Group, Match, Bet, Score, UserRanking, LOGGER,\
    BettableEvent, generate_matchs, compute_event_ranking, compute_group_ranking,\
    compute_overall_ranking, generate_events, WinnerSetup, PointsSetup,\
    Attributes, Winner, Participant
from django.http.response import HttpResponse, HttpResponseForbidden,\
    HttpResponseBadRequest
from django.contrib.auth.models import User
import datetime
from datetime import datetime as dt
from seq_common.utils import dates
import traceback
from django.db.models.aggregates import Sum
import json
from django.core.exceptions import PermissionDenied
from bets import utilities
from bets.utilities import generates_per_participant_result,\
    compute_fifa_wc_pools, compute_fifa_wc_8th, complete_meta_for_type, get_event_meta


COUNT_PER_STEP = {'MATCH_SIXTEENTH': 32,
                  'MATCH_EIGHTH': 16,
                  'MATCH_QUARTER': 8,
                  'MATCH_SEMIFINAL': 4,
                  'MATCH_FINAL' : 2,
                  'MATCH_THIRDPLACE' : 2,
                  'MATCH_WINNER' : 1
                  }

def index(request):
    now = datetime.datetime.today()
    begin = dt.combine(datetime.date.today(), dt.min.time())
    end = dt.combine(dates.AddDay(begin, 14), dt.max.time())
    all_dates = Match.objects.filter(when__gte=begin, when__lte=end).order_by('when').dates('when','day')
    all_dates = [a_date.strftime('%Y-%m-%d') for a_date in all_dates]
    active_events = BettableEvent.objects.filter(end_date__gte=datetime.date.today).order_by('name')
    if request.user.is_authenticated and request.user.id!=None:
        user = User.objects.get(id=request.user.id)
        rankings = UserRanking.objects.filter(owner__id=user.id)
        if not rankings.exists():
            initial_ranking = UserRanking()
            initial_ranking.owner = user
            initial_ranking.group = None
            initial_ranking.overall_score = 0
            initial_ranking.rank = None
            initial_ranking.save()
            rankings = UserRanking.objects.filter(owner__id=user.id)
        global_ranking = UserRanking.objects.filter(owner__id=user.id, group=None)
        if global_ranking.exists():
            global_ranking = global_ranking[0]
        else:
            global_ranking = None

        admin_groups = Group.objects.filter(Q(owners__id__exact=request.user.id)).distinct().order_by('name')
        member_groups = Group.objects.filter(Q(members__id__exact=request.user.id) | Q(owners__id__exact=request.user.id)).distinct().order_by('name')

        winner_setups = []
        for group in list(admin_groups) + list(member_groups):
            setup = WinnerSetup.objects.filter(group__id=group.id, group__event__end_date__gte=now)
            if setup.exists():
                setup = setup[0]
                all_steps = setup.setup.all()
                if all_steps.exists():
                    if not group.event.id in winner_setups:
                        winner_setups.append(group.event.id)

        all_matches = Match.objects.filter(when__gte=begin, when__lte=end).order_by('when')
        all_bets = {}
        for match in all_matches:
            bet = Bet.objects.filter(owner__id=request.user.id, match__id=match.id)
            if bet.exists():
                bet = bet[0]
            else:
                bet = Bet()
                bet.clean()
                bet.owner = user
                bet.match = match
                bet.when = datetime.datetime.now()
                bet.winner = None
                score = Score()
                score.name = match.name
                score.first = 0
                score.second = 0
                score.save()
                bet.result = score
                bet.save()
            all_bets[bet.match.id] = {'id': bet.id, 'score': {'first':bet.result.first, 'second':bet.result.second}, 'enabled':str(bet.match.when + datetime.timedelta(minutes=10)>=now).lower(), 'amount': bet.amount if bet.amount!=None else 0}
        allow_amount = request.user.groups.filter(name='allow_amount')

        context = {'winner_setups': winner_setups, 'admin_groups': admin_groups,'member_groups': member_groups, 'all_dates': all_dates, 'all_bets': all_bets, 'rankings': rankings, 'global_rank':global_ranking, 'events': active_events, 'allow_amount': allow_amount, 'events': active_events}
    else:
        context = {'all_dates': all_dates, 'events': active_events, 'all_bets': []}
    return render(request,'index.html', context)

def bets_winner_save(request):
    if request.user.is_authenticated and request.user.id!=None:
        group_id = request.POST['group_id']
        user = User.objects.get(id=request.user.id)
        try:
            group = Group.objects.get(id=group_id)
            if group.owners.filter(id=user.id).exists():
                data = request.POST['data']
                data = json.loads(data)
                first = True
                for row in data:
                    if first:
                        winner_setup = WinnerSetup.objects.filter(group__id=group.id)
                        if winner_setup.exists():
                            winner_setup = winner_setup[0]
                            for p_setup in winner_setup.setup.all():
                                p_setup.delete()
                            winner_setup.setup.clear()
                        else:
                            winner_setup = WinnerSetup()
                            winner_setup.group = group
                            winner_setup.clean()
                            winner_setup.save()
                        first = False
                    point_setup = PointsSetup()
                    point_setup.category = Attributes.objects.get(identifier=row[u'step'])
                    point_setup.points = row[u'points']
                    point_setup.use_quotes = row[u'quote']
                    point_setup.save()
                    winner_setup.setup.add(point_setup)
                    winner_setup.save()
                return HttpResponse('{"result": true, "message":"Saved"}', content_type="application/json");
            else:
                raise PermissionDenied()
        except:
            traceback.print_exc()
            return HttpResponseBadRequest()
    else:
        raise PermissionDenied()

def bets_save(request):
    if request.user.is_authenticated and request.user.id!=None:
        message = "Aucun probleme."
        user = User.objects.get(id=request.user.id)
        now = dt.now()
        all_bets = json.loads(request.POST['all_bets'])
        for bet in all_bets:
            web_bet = all_bets[bet]
            bet_id = web_bet[u'id']
            user_bet = Bet.objects.get(id=bet_id, owner__id=user.id)
            if user_bet.match.when+ datetime.timedelta(minutes=10)>=now:
                score = Score.objects.get(id=user_bet.result.id)
                user_bet.when = now
                score.first = web_bet[u'score'][u'first']
                score.second = web_bet[u'score'][u'second']
                score.save()
                if score.first==score.second:
                    user_bet.winner = None
                elif score.first>score.second:
                    user_bet.winner = user_bet.match.first
                else:
                    user_bet.winner = user_bet.match.second
                user_bet.amount = web_bet[u'amount'] if web_bet.has_key(u'amount') else 0
                user_bet.save()
            else:
                LOGGER.warn("Tried to bet after date")
                message = "Un ou plusieurs matchs ont deja commence."
    return HttpResponse('{"result": true, "message":"' + message + '"}', content_type="application/json");

def event_view(request):
    viewed_user = None
    if request.GET.has_key('user_id'):
        user_id = request.GET['user_id']
        viewed_user = User.objects.get(id=user_id)
    event_id = request.GET['event_id']
    event = BettableEvent.objects.get(id=event_id)
    event_data = utilities.get_event_meta(event)
    context = {"event": event, "event_data": event_data, "viewed_user": viewed_user}
    return render(request,'event_view.html', context)

def group_winner_bet_save(request):
    if request.user.is_authenticated and request.user.id!=None:
        bet_identifier = request.POST['category']
        bet_data = json.loads(request.POST['data'])
        event_id = request.POST['event_id']
        winner_bet = Winner.objects.filter(owner__id=request.user.id, event__id=event_id, category__identifier=bet_identifier)
        if winner_bet.exists():
            winner_bet = winner_bet[0]
            winner_bet.participants.clear()
            winner_bet.save()
        else:
            winner_bet = Winner()
            winner_bet.owner = User.objects.get(id=request.user.id)
            winner_bet.event = BettableEvent.objects.get(id=event_id)
            winner_bet.category = Attributes.objects.get(identifier=bet_identifier, type='match_type')
            winner_bet.save()
        for participant_id in bet_data:
            winner_bet.participants.add(Participant.objects.get(id=participant_id))
        winner_bet.save()
        return HttpResponse('{"result": true, "message":"Aucun probleme"}', content_type="application/json");
    else:
        raise PermissionDenied()

def group_winner_bet(request):
    if request.user.is_authenticated and request.user.id!=None:
        now = datetime.date.today()
        event_id = request.GET['event_id']
        event = BettableEvent.objects.get(id=event_id)
        admin_groups = Group.objects.filter(owners__id__exact=request.user.id,event__id=event_id).distinct().order_by('name')
        member_groups = Group.objects.filter(Q(members__id__exact=request.user.id) | Q(owners__id__exact=request.user.id), Q(event__id=event_id)).distinct().order_by('name')
        winner_setups = []
        all_setups = WinnerSetup.objects.filter(group__in=list(admin_groups) + list(member_groups))
        for setup in all_setups:
            all_steps = setup.setup.all().order_by('id').values_list('category__identifier', flat=True)
            for step in all_steps:
                if not step in winner_setups:
                    winner_setups.append(step)
        if len(winner_setups)==0:
            winner_setups = None
        event_meta = get_event_meta(event)
        match_types = Attributes.objects.filter(active=True, type='match_type').order_by('id')
        winners_bets = Winner.objects.filter(event__id=event_id, owner__id=request.user.id)
        bets_data = {}
        limits_data = {}
        for bet in winners_bets:
            bets_data[bet.category.identifier] = []
            limits_data[bet.category.identifier] = event_meta['bets_delays'][bet.category.identifier]>=(now - event.start_date).days
            for participant in bet.participants.all():
                bets_data[bet.category.identifier].append(participant.id)
                
        context = {'event_data': event_meta, 'steps_count': COUNT_PER_STEP, 'event': event, 'winner_setups': winner_setups, 'match_types':match_types, 'bets_data': bets_data, 'limits_data': limits_data}
        return render(request,'group_winner_bet.html', context)
    else:
        raise PermissionDenied()

def group_edit(request):
    if request.user.is_authenticated and request.user.id!=None:
        group_id = request.GET['group_id']
        user = User.objects.get(id=request.user.id)
        now = dt.now()
        try:
            group = Group.objects.get(id=group_id)
            if group.owners.filter(id=user.id).exists():
                all_members = list(group.members.all()) + list(group.owners.all())
                for member in all_members:
                    rank = UserRanking.objects.filter(owner__id=member.id, group__id=group.id)
                    if not rank.exists():
                        rank = UserRanking()
                        rank.owner = member
                        rank.group = group
                        rank.overall_score = 0
                        rank.rank = None
                        rank.save()
                    else:
                        rank = rank[0]
                all_users = list(group.members.values_list('id', flat=True)) + list(group.owners.values_list('id', flat=True))
                all_matchs = group.event.matchs.all().values_list('id', flat=True)
                betted_amounts = {}
                for user_id in all_users:
                    betted_amounts[user_id] = Bet.objects.filter(owner__id=user_id, match__id__in=all_matchs).aggregate(Sum('amount'))['amount__sum']
                locked_amounts = {}
                for user_id in all_users:
                    locked_amounts[user_id] = Bet.objects.filter(owner__id=user_id, match__id__in=all_matchs, match__when__lte=now).aggregate(Sum('amount'))['amount__sum']
                    
                ranking = UserRanking.objects.filter(owner__id__in=all_users, group__id=group.id)
                your_rank = UserRanking.objects.get(owner__id=user.id, group__id=group.id)
                allow_amount = request.user.groups.filter(name='allow_amount')
                winner_setup = WinnerSetup.objects.filter(group__id=group.id)
                if winner_setup.exists():
                    winner_setup = winner_setup[0]
                else:
                    winner_setup = None
                
                context = {'group': group, 'ranking':ranking, 'yours': your_rank, 'betted_amounts':betted_amounts, 'allow_amount':allow_amount,'locked_amounts':locked_amounts, 'winner_setup': winner_setup}
                return render(request,'group_edit.html', context)
            else:
                raise PermissionDenied()
        except:
            traceback.print_exc()
            return HttpResponseBadRequest()
    else:
        raise PermissionDenied()

def group_details(request):
    if request.user.is_authenticated and request.user.id!=None:
        group_id = request.GET['group_id']
        user = User.objects.get(id=request.user.id)
        group = Group.objects.get(id=group_id)
        if group.members.filter(id=user.id).exists() or group.owners.filter(id=user.id).exists():
            allow_amount = request.user.groups.filter(name='allow_amount')
            all_users_ids = list(group.members.values_list('id', flat=True)) + list(group.owners.values_list('id', flat=True))
            all_users = User.objects.filter(id__in=all_users_ids).order_by('id')
            all_matchs = group.event.matchs.all().order_by('when')
            all_bets = {}
            for match in all_matchs:
                bets = Bet.objects.filter(match__id=match.id, owner__in=all_users_ids).order_by('owner__id')
                all_bets[match.name] = bets
            context = {'all_bets':all_bets, 'all_users': all_users, 'all_matchs': all_matchs, 'today': datetime.date.today().strftime('%Y-%m-%d'), 'allow_amount': allow_amount}
            return render(request,'group_details.html', context) 
    raise PermissionDenied()
            

def group_compare(request):
    if request.user.is_authenticated and request.user.id!=None:
        group_id = request.GET['group_id']
        bet_date_start = datetime.datetime.strptime(request.GET['date'],'%Y-%m-%d').replace(hour=0, minute=0, second=0)
        bet_date_end = datetime.datetime.strptime(request.GET['date'],'%Y-%m-%d').replace(hour=23, minute=59, second=59)
        
        group = Group.objects.get(id=group_id)
        all_members = list(group.members.all()) + list(group.owners.all())
        bets = {}
        all_matchs = group.event.matchs.filter(when__gte=bet_date_start, when__lte=bet_date_end)
        for match in all_matchs:
            bets[match.name] = {}
            for member in all_members:
                bet = Bet.objects.get(match__id=match.id, owner__id=member.id)
                bets[match.name][str(member.id)] = {'first':bet.result.first, 'second':bet.result.second, 'amount':bet.amount}
        return render(request,'rendition/bets_compare.html', {'bets':bets,'all_members': all_members})
    else:
        raise PermissionDenied()
    
def group_view(request):
    if request.user.is_authenticated and request.user.id!=None:
        group_id = request.GET['group_id']
        user = User.objects.get(id=request.user.id)
        now = dt.now()
        try:
            group = Group.objects.get(id=group_id)
            if group.members.filter(id=user.id).exists() or group.owners.filter(id=user.id).exists():
                all_members = list(group.members.all()) + list(group.owners.all())
                for member in all_members:
                    rank = UserRanking.objects.filter(owner__id=member.id, group__id=group.id)
                    if not rank.exists():
                        rank = UserRanking()
                        rank.owner = member
                        rank.group = group
                        rank.overall_score = 0
                        rank.rank = None
                        rank.save()
                    else:
                        rank = rank[0]
                all_users = list(group.members.values_list('id', flat=True)) + list(group.owners.values_list('id', flat=True))
                all_matchs = group.event.matchs.all().values_list('id', flat=True)

                betted_amounts = {}
                for user_id in all_users:
                    betted_amounts[user_id] = Bet.objects.filter(owner__id=user_id, match__id__in=all_matchs).aggregate(Sum('amount'))['amount__sum']
                locked_amounts = {}
                for user_id in all_users:
                    locked_amounts[user_id] = Bet.objects.filter(owner__id=user_id, match__id__in=all_matchs, match__when__lte=now).aggregate(Sum('amount'))['amount__sum']
                    
                ranking = UserRanking.objects.filter(owner__id__in=all_users, group__id=group.id)
                your_rank = UserRanking.objects.filter(owner__id=user.id, group__id=group.id)
                if your_rank.exists():
                    your_rank = your_rank[0]
                allow_amount = request.user.groups.filter(name='allow_amount')
                context = {'group': group, 'ranking':ranking, 'yours': your_rank, 'betted_amounts':betted_amounts, 'allow_amount':allow_amount,
                           'locked_amounts':locked_amounts}
                return render(request,'group_view.html', context)
            else:
                raise PermissionDenied()
        except:
            traceback.print_exc()
            return HttpResponseBadRequest()
    else:
        raise PermissionDenied()

def group_remove_user(request):
    if request.user.is_authenticated and request.user.id!=None:
        group_id = request.POST['group_id']
        removed_user_id = request.POST['user_id']
        user = User.objects.get(id=request.user.id)
        try:
            group = Group.objects.get(id=group_id)
            removed_user = User.objects.get(id=removed_user_id)
            if group.owners.filter(id=user.id).exists():
                group.members.remove(removed_user)
                group.save()
                return HttpResponse('{"result": true, "message":"User removed!"}', content_type="application/json");
            else:
                raise PermissionDenied()
        except:
            traceback.print_exc()
            return HttpResponseBadRequest()
    else:
        raise PermissionDenied()

def group_join(request):
    group_name = request.POST['group_name']
    user = User.objects.get(id=request.user.id)
    if Group.objects.filter(name=group_name).exists():
        if Group.objects.filter(Q(name=group_name), Q(members__id__exact=request.user.id) | Q(owners__id__exact=request.user.id)).exists():
            return HttpResponse('{"result": true, "message":"Group already joined!"}', content_type="application/json");
        else:
            joined_group = Group.objects.get(name=group_name)
            joined_group.members.add(user)
            joined_group.save()
        return HttpResponse('{"result": true, "message":"Group joined!"}', content_type="application/json");
    else:
        return HttpResponse('{"result": false, "message":"Group doesn''t exist!"}', content_type="application/json");

def group_create(request):
    group_name = request.POST['group_name']
    event_id = request.POST['event_id']
    user = User.objects.get(id=request.user.id)
    if Group.objects.filter(name=group_name).exists():
        return HttpResponse('{"result": false, "message":"Group name already exists!"}', content_type="application/json");
    else:
        group = Group()
        group.many_fields = {}
        group.name = group_name
        group.event = BettableEvent.objects.get(id=event_id)
        group.save()
        group.owners.add(user)
        group.save()
        return HttpResponse('{"result": true, "message":"No problem occured."}', content_type="application/json");

def matchs_compute(request):
    if request.user.id!=None and request.user.is_authenticated and request.user.is_superuser:
        compute_event_ranking()
        compute_group_ranking()
        compute_overall_ranking()
        return HttpResponse('{"result": true, "message":"No problem occured."}', content_type="application/json");
    else:
        raise PermissionDenied()
        
def matchs_save(request):
    if request.user.id!=None and request.user.is_authenticated and request.user.is_superuser:
        message = "Aucun probleme."
        all_matchs = json.loads(request.POST['all_matchs'])
        event_id = request.POST['event_id']
        for match in all_matchs:
            LOGGER.info("Working on match " + str(match))
            web_match = all_matchs[match]
            py_match = Match.objects.get(id=match)
            if py_match.result==None:
                score = Score()
            else:
                score = Score.objects.get(id=py_match.result.id)
            score.first = web_match[u'score'][u'first']
            score.second = web_match[u'score'][u'second']
            score.name = "Official score " + py_match.name
            score.save()
                
            py_match.result = score
            py_match.save()
        generate_matchs(all_matchs.keys())
        event = BettableEvent.objects.get(id=event_id)
        generates_per_participant_result(event)
        # TODO: Change
        compute_fifa_wc_pools(event)
        compute_fifa_wc_8th(event)
        event_meta = get_event_meta(event)
        for m_type in event_meta['final_phases'][1:]:
            complete_meta_for_type(event, m_type)
        return HttpResponse('{"result": true, "message":"' + message + '"}', content_type="application/json");
    else:
        raise PermissionDenied()

def matchs_generate(request):
    if request.user.id!=None and request.user.is_authenticated and request.user.is_superuser:
        generate_events()
        generate_matchs()
        return HttpResponse('{"result": true, "message":"No problem"}', content_type="application/json");
    else:
        raise PermissionDenied()

def matchs_schedule_update(request):
    if request.user.id!=None and request.user.is_authenticated and request.user.is_superuser:
        match_id = request.POST['match_id']
        new_date = request.POST['new_date']
        new_time = request.POST['new_time']
        new_full_date = new_date + ' ' + new_time
        new_full_date = dt.strptime(new_full_date, '%Y-%m-%d %H:%M')
        match = Match.objects.get(id=match_id)
        match.when = new_full_date
        match.save()
        generate_events()
        generate_matchs()
        return HttpResponse('{"result": true, "message":"No problem"}', content_type="application/json");
    else:
        raise PermissionDenied()

def matchs_schedule(request):
    if request.user.id!=None and request.user.is_authenticated and request.user.is_superuser:
        begin = dt.combine(dates.AddDay(datetime.date.today(),-31), dt.min.time())
        end = dt.combine(dates.AddDay(datetime.date.today(), 31), dt.max.time())
        all_matchs = Match.objects.filter(when__gte=begin, when__lte=end).order_by('when')
        context = {'all_matchs': all_matchs}
        return render(request,'match_schedule.html', context)
    else:
        raise PermissionDenied()
        
def matchs_edit(request):
    begin = dt.combine(dates.AddDay(datetime.date.today(),-31), dt.min.time())
    end = dt.combine(dates.AddDay(datetime.date.today(), 14), dt.max.time())
    active_events = BettableEvent.objects.filter(end_date__gte=begin).order_by('name')
    all_dates = Match.objects.filter(when__gte=begin, when__lte=end).order_by('when').dates('when','day')
    all_dates = [a_date.strftime('%Y-%m-%d') for a_date in all_dates]
    context = {'all_dates': all_dates, 'events': active_events}
    return render(request,'match_edit.html', context)

def profile_show(request):
    return render(request,'profile_show.html', {})

def badrequest(request):
    return render(request,'errors/400.html', {})

def forbidden(request):
    return render(request,'errors/403.html', {})