from django.db.models import Q
from django.shortcuts import render, redirect

from bets.models import Group, Match, Bet, Score
from django.http.response import HttpResponse
from django.contrib.auth.models import User
import datetime
from datetime import datetime as dt
from seq_common.utils import dates
import simplejson

def index(request):
    if request.user.is_authenticated and request.user.id!=None:
        user = User.objects.get(id=request.user.id)
        now = dt.combine(datetime.date.today(), dt.min.time())
        end = dt.combine(dates.AddDay(now, 14), dt.max.time())
        admin_groups = Group.objects.filter(Q(owners__id__exact=request.user.id)).order_by('name')
        member_groups = Group.objects.filter(Q(members__id__exact=request.user.id)).order_by('name')
        all_dates = Match.objects.filter(when__gte=now, when__lte=end).order_by('when').dates('when','day')
        all_dates = [a_date.strftime('%Y-%m-%d') for a_date in all_dates]
        all_matches = Match.objects.filter(when__gte=now, when__lte=end).order_by('when')
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
            all_bets[bet.match.id] = {'id': bet.id, 'score': {'first':bet.result.first, 'second':bet.result.second}}
        context = {'admin_groups': admin_groups,'member_groups': member_groups, 'all_dates': all_dates, 'all_bets': all_bets}
    else:
        context = {}
    return render(request,'index.html', context)

def save_bets(request):
    if request.user.is_authenticated and request.user.id!=None:
        user = User.objects.get(id=request.user.id)
        now = dt.now()
        all_bets = simplejson.loads(request.POST['all_bets'])
        for bet in all_bets:
            web_bet = all_bets[bet]
            bet_id = web_bet[u'id']
            user_bet = Bet.objects.get(id=bet_id, owner__id=user.id)
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
            user_bet.save()
    return HttpResponse('{"result": true, "message":"No problem occured."}', content_type="application/json");

def group_create(request):
    group_name = request.POST['group_name']
    user = User.objects.get(id=request.user.id)
    if Group.objects.filter(name=group_name).exists():
        return HttpResponse('{"result": false, "message":"Group name already exists!"}', content_type="application/json");
    else:
        group = Group()
        group.name = group_name
        group.save()
        group.owners.add(user)
        group.save()
        return HttpResponse('{"result": true, "message":"No problem occured."}', content_type="application/json");
    
def group_show(request):
    None