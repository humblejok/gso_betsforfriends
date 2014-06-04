from django.db.models import Q
from django.shortcuts import render

from bets.models import Group
from django.http.response import HttpResponse
from django.contrib.auth.models import User

def index(request):
    if request.user.is_authenticated and request.user.id!=None:
        admin_groups = Group.objects.filter(Q(owners__id__exact=request.user.id)).order_by('name')
        member_groups = Group.objects.filter(Q(members__id__exact=request.user.id)).order_by('name')
        context = {'admin_groups': admin_groups,'member_groups': member_groups}
    else:
        context = {}
    return render(request,'index.html', context)

def group_create(request):
    group_name = request.POST['group_name']
    print group_name
    user = User.objects.get(id=request.user.id)
    if Group.objects.filter(name=group_name).exists():
        return HttpResponse('{"result": false, "message":"Group name already exists"}', content_type="application/json");
    else:
        group = Group()
        group.name = group_name
        group.save()
        group.owners.add(user)
        group.save()
        return HttpResponse('{"result": true, "message":"Group name already exists"}', content_type="application/json");
    
def group_show(request):
    None