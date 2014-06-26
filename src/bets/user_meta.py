'''
Created on 25 juin 2014

@author: humble_jok
'''
from bets.utilities import MONGO_URL
from pymongo.mongo_client import MongoClient
from allauth.socialaccount.models import SocialAccount
import hashlib
import uuid

client = MongoClient(MONGO_URL)

def initialize_user_meta(user):
    client['bets']['users'].remove({'_id': user.id})
    social_account = SocialAccount.objects.filter(user__id=user.id)
    if social_account.exists():
        uid = social_account[0].uid
    else:
        uid = user.first_name + '-' + user.last_name + '-' + str(user.id) + str(uuid.uuid4())
    token = hashlib.sha1()
    token.update('BetsForFriends')
    token.update(uid)
    social_token = token.hexdigest()
    user_meta = {'user': {'first_name': user.first_name, 'last_name': user.last_name, 'id': user.id}, 'token': social_token, '_id': user.id}
    
    client['bets']['users'].insert(user_meta)
    
def print_meta(meta):
    if isinstance(meta, list):
        as_string = '['
        first = True
        for item in meta:
            if not first:
                as_string += ','
            first = False
            as_string += print_meta(item)
        as_string += ']'
        return as_string
    elif isinstance(meta, dict):
        as_string = '{'
        first = True
        for item in meta:
            if not first:
                as_string += ','
            first = False
            as_string += '"' + item.encode('ascii','replace') + '":' + print_meta(meta[item])
        as_string += '}'
        return as_string
    elif isinstance(meta, basestring):
        return '"' + meta.encode('ascii','replace') + '"'
    else:
        return str(meta)        
    
def get_user_meta(user = None, token = None):
    if user!=None:
        return client['bets']['users'].find_one({'_id': user.id})
    elif token!=None:
        return client['bets']['users'].find_one({'token': token})
    else:
        return None

def get_user_meta_web(user = None, token = None):
    if user!=None:
        data = client['bets']['users'].find_one({'_id': user.id})
        return print_meta(data)
    elif token!=None:
        data = client['bets']['users'].find_one({'token': token})
        return print_meta(data)
    else:
        return None
    

