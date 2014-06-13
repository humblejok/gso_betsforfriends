from django.db.models import Q
from django.shortcuts import render, redirect

from bets.models import Group, Match, Bet, Score, UserRanking, LOGGER,\
    BettableEvent
from django.http.response import HttpResponse
from django.contrib.auth.models import User
import datetime
from datetime import datetime as dt
from seq_common.utils import dates
from django.utils import simplejson
import traceback

def index(request):
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
        now = datetime.datetime.today()
        begin = dt.combine(datetime.date.today(), dt.min.time())
        end = dt.combine(dates.AddDay(begin, 14), dt.max.time())
        admin_groups = Group.objects.filter(Q(owners__id__exact=request.user.id)).distinct().order_by('name')
        member_groups = Group.objects.filter(Q(members__id__exact=request.user.id) | Q(owners__id__exact=request.user.id)).distinct().order_by('name')
        all_dates = Match.objects.filter(when__gte=begin, when__lte=end).order_by('when').dates('when','day')
        all_dates = [a_date.strftime('%Y-%m-%d') for a_date in all_dates]
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
            all_bets[bet.match.id] = {'id': bet.id, 'score': {'first':bet.result.first, 'second':bet.result.second}, 'enabled':str(bet.match.when>=now).lower(), 'amount': bet.amount if bet.amount!=None else 0}
        active_events = BettableEvent.objects.filter(end_date__gte=datetime.date.today).order_by('name')
        context = {'admin_groups': admin_groups,'member_groups': member_groups, 'all_dates': all_dates, 'all_bets': all_bets, 'rankings': rankings, 'global_rank':global_ranking, 'events': active_events}
        print context
    else:
        context = {}
    return render(request,'index.html', context)

def bets_save(request):
    if request.user.is_authenticated and request.user.id!=None:
        message = "Aucun probleme."
        user = User.objects.get(id=request.user.id)
        now = dt.now()
        all_bets = simplejson.loads(request.POST['all_bets'])
        for bet in all_bets:
            web_bet = all_bets[bet]
            bet_id = web_bet[u'id']
            user_bet = Bet.objects.get(id=bet_id, owner__id=user.id)
            if user_bet.match.when>=now:
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
                user_bet.amount = web_bet[u'amount']
                user_bet.save()
            else:
                LOGGER.warn("Tried to bet after date")
                message = "Un ou plusieurs matchs ont deja commence."
    return HttpResponse('{"result": true, "message":"' + message + '"}', content_type="application/json");

def group_edit(request):
    redirect('index.html')
    
def group_view(request):
    if request.user.is_authenticated and request.user.id!=None:
        group_id = request.GET['group_id']
        user = User.objects.get(id=request.user.id)
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
                ranking = UserRanking.objects.filter(owner__id__in=all_users, group__id=group.id)
                your_rank = UserRanking.objects.get(owner__id=user.id, group__id=group.id)
                context = {'group': group, 'ranking':ranking, 'yours': your_rank}
                return render(request,'group_view.html', context)
            else:
                redirect('index.html')
        except:
            traceback.print_exc()
            redirect('index.html')
    else:
        redirect('index.html')

def group_join(request):
    group_name = request.POST['group_name']
    user = User.objects.get(id=request.user.id)
    if Group.objects.filter(name=group_name).exists():
        print "Group found"
        if Group.objects.filter(Q(name=group_name), Q(members__id__exact=request.user.id) | Q(owners__id__exact=request.user.id)).exists():
            return HttpResponse('{"result": true, "message":"Group already joined!"}', content_type="application/json");
        else:
            joined_group = Group.objects.get(name=group_name)
            joined_group.members.add(user)
            joined_group.save()
        return HttpResponse('{"result": true, "message":"Group joined!"}', content_type="application/json");
    else:
        print "Group not found"
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

def matchs_save(request):
    if request.user.id!=None and request.user.is_authenticated and request.user.is_superuser:
        message = "Aucun probleme."
        all_matchs = simplejson.loads(request.POST['all_matchs'])
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
    return HttpResponse('{"result": true, "message":"' + message + '"}', content_type="application/json");

def matchs_generate(request):
    if request.user.id!=None and request.user.is_authenticated and request.user.is_superuser:
        message = "Aucun probleme."
        all_matchs = simplejson.loads(request.POST['all_matchs'])
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
    return HttpResponse('{"result": true, "message":"' + message + '"}', content_type="application/json");

def matchs_edit(request):
    begin = dt.combine(dates.AddDay(datetime.date.today(),-180), dt.min.time())
    end = dt.combine(dates.AddDay(datetime.date.today(), 14), dt.max.time())
    all_dates = Match.objects.filter(when__gte=begin, when__lte=end).order_by('when').dates('when','day')
    all_dates = [a_date.strftime('%Y-%m-%d') for a_date in all_dates]
    context = {'all_dates': all_dates}
    return render(request,'match_edit.html', context)