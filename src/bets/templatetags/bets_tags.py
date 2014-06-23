'''
Created on 10 mars 2014

@author: humble_jok
'''
from django import template
from bets.models import Attributes

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

@register.filter()   
def get_list_element(a_list, index):
    index = int(index)
    if index>=0 and index<len(a_list):
        return a_list[index]
    else:
        return None

@register.filter()
def get_range(num):
    return range(num)

@register.filter()
def multiply(initial, mult):
    return initial * mult


@register.filter()
def divide(initial, div):
    return initial / div

@register.filter()
def get_downshifts(initial, current):
    if initial==current:
        return 0
    return get_downshifts(initial, current * 2) + (initial / (current * 2))

@register.filter()
def get_attribute(attr_type, attr_ident):
    return Attributes.objects.get(type=attr_type, identifier=attr_ident)