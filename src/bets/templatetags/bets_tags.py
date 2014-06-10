'''
Created on 10 mars 2014

@author: humble_jok
'''
from django import template

register = template.Library()

@register.filter()
def get_match_name(match_name):
    return match_name.encode('ascii','replace')
