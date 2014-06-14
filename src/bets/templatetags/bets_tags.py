'''
Created on 10 mars 2014

@author: humble_jok
'''
from django import template

register = template.Library()

@register.filter()
def get_match_name(match_name):
    return match_name.encode('ascii','replace')

@register.filter()
def get_dict_key(d, key):
    if d.has_key(key):
        return d[key]
    elif d.has_key(str(key)):
        return d[str(key)]
    elif d.has_key(unicode(key)):
        return d[unicode(key)]
    else:
        return None

