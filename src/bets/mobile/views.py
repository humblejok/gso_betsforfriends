'''
Created on 25 juin 2014

@author: humble_jok
'''
from django.core.exceptions import PermissionDenied
from django.http.response import HttpResponse
from bets.user_meta import get_user_meta, initialize_user_meta,\
    get_user_meta_web
from gso_betsforfriends import settings
from django.contrib.auth.models import User
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def login(request):
    if request.POST.has_key('token'):
        token = request.POST['token']
        if (settings.DEBUG or request.is_secure()) and get_user_meta(None,token)!=None:
            return HttpResponse('{"result": true, "message":"Token is valid", "meta":' + get_user_meta_web(None,token) + '}', content_type="application/json");
    raise PermissionDenied()

def user_initialize(request):
    if (settings.DEBUG or request.is_secure()) and request.user.is_authenticated:
        initialize_user_meta(User.objects.get(id=request.user.id))
        return HttpResponse('{"result": true, "message":"Done"}')
    raise PermissionDenied()


def user_token(request):
    if (settings.DEBUG or request.is_secure()) and request.user.is_authenticated:
        context = {'user_meta': get_user_meta(User.objects.get(id=request.user.id),None)}
        return render(request,'mobile/user_token.html', context)
    else:
        raise PermissionDenied()
    
@csrf_exempt
def bets_get(request):
    if request.POST.has_key('token'):
        token = request.POST['token']
        if (settings.DEBUG or request.is_secure()) and get_user_meta(None,token)!=None:
            return HttpResponse('{"result": true, "message":"Token is valid", "meta":' + str(get_user_meta(None,token)) + '}', content_type="application/json");
    raise PermissionDenied()