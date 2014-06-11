from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.db.models.fields import FieldDoesNotExist
from django.template import loader
from openpyxl.reader.excel import load_workbook
from seq_common.utils import classes, dates
from datetime import datetime as dt

import datetime
import logging
import os
import traceback
from django.template.context import Context
from gso_betsforfriends.settings import RESOURCES_MAIN_PATH, STATICS_PATH
from django.db.models.aggregates import Sum

LOGGER = logging.getLogger(__name__)

def setup():
    populate_attributes_from_xlsx('bets.models.Attributes', os.path.join(RESOURCES_MAIN_PATH,'Repository Setup.xlsx'))
    generate_attributes()
    populate_model_from_xlsx('bets.models.Participant', os.path.join(RESOURCES_MAIN_PATH,'Repository Setup.xlsx'))
    populate_model_from_xlsx('bets.models.Match', os.path.join(RESOURCES_MAIN_PATH,'Repository Setup.xlsx'))
    populate_model_from_xlsx('bets.models.BettableEvent', os.path.join(RESOURCES_MAIN_PATH,'Repository Setup.xlsx'))

def generate_attributes():
    all_types = Attributes.objects.all().order_by('type').distinct('type')
    for a_type in all_types:
        all_elements = Attributes.objects.filter(type=a_type.type, active=True)
        context = Context({"selection": all_elements})
        template = loader.get_template('rendition/attributes_option_renderer.html')
        rendition = template.render(context)
        # TODO Implement multi-langage
        outfile = os.path.join(STATICS_PATH, 'attributes', a_type.type + '_en.html')
        with open(outfile,'w') as o:
            o.write(rendition.encode('utf-8'))
            
def generate_events():
    now = dt.combine(datetime.date.today(), dt.min.time())
    all_dates = Match.objects.filter(when__gte=now).order_by('when').dates('when','day')
    template = loader.get_template('rendition/events.html')
    for a_date in all_dates:
        events = Match.objects.filter(when__gte=dt.combine(a_date, dt.min.time()), when__lte=dt.combine(a_date, dt.max.time())).order_by('when')
        context = Context({"events": events})
        rendition = template.render(context)
        outfile = os.path.join(STATICS_PATH,'events', a_date.strftime('%Y-%m-%d') + '_en.html')
        with open(outfile,'w') as o:
            o.write(rendition.encode('utf-8'))
            
def generate_matchs():
    now = dt.combine(datetime.date.today(), dt.min.time())
    all_dates = Match.objects.filter(when__gte=now).order_by('when').dates('when','day')
    template = loader.get_template('rendition/matchs.html')
    for a_date in all_dates:
        events = Match.objects.filter(when__gte=dt.combine(a_date, dt.min.time()), when__lte=dt.combine(a_date, dt.max.time())).order_by('when')
        context = Context({"events": events})
        rendition = template.render(context)
        outfile = os.path.join(STATICS_PATH,'matchs', a_date.strftime('%Y-%m-%d') + '_en.html')
        with open(outfile,'w') as o:
            o.write(rendition.encode('utf-8'))

def populate_attributes_from_xlsx(model_name, xlsx_file):
    model = classes.my_class_import(model_name)
    workbook = load_workbook(xlsx_file)
    sheet = workbook.get_sheet_by_name(name=model.__name__)
    row_index = 1
    # Reading header
    header = []
    for column_index in range(1, sheet.get_highest_column()+1):
        value = sheet.cell(row = row_index, column=column_index).value
        if value!=None:
            header.append(value if value!='' else header[-1])
        else:
            break
    LOGGER.info('Using header:' + str(header))
    row_index += 1
    while row_index<=sheet.get_highest_row():
        if model.objects.filter(identifier=sheet.cell(row = row_index, column = 1).value).exists():
            instance = model.objects.get(identifier=sheet.cell(row = row_index, column = 1).value)
        else:
            instance = model()
        for i in range(0,len(header)):
            value = sheet.cell(row = row_index, column = i+1).value
            setattr(instance, header[i], value)
        if instance.identifier==None:
            break
        else:
            instance.save()
        row_index += 1

def populate_model_from_xlsx(model_name, xlsx_file):
    LOGGER.info("Loading data in " + model_name)
    model = classes.my_class_import(model_name)
    workbook = load_workbook(xlsx_file)
    sheet = workbook.get_sheet_by_name(name=model.__name__)
    row_index = 1
    # Reading header
    header = []
    for column_index in range(1, sheet.get_highest_column() + 1):
        value = sheet.cell(row = row_index, column=column_index).value
        if value!=None:
            header.append(value if value!='' else header[-1])
        else:
            break
    LOGGER.info('Using header:' + str(header))
    row_index += 1
    while row_index<=sheet.get_highest_row():
        instance = model()
        for i in range(0,len(header)):
            value = sheet.cell(row = row_index, column = i + 1).value
            field_info = Attributes()
            field_info.short_name = header[i]
            field_info.name = header[i]
            instance.set_attribute('excel', field_info, value)
        instance.finalize()
        if instance.name==None:
            break
        else:
            instance.save()
        row_index += 1
        
def rank_list(rank_list):
    ordered = sorted(rank_list, key=lambda x: x.overall_score, reverse=True)
    ranking = 1
    for rank in ordered:
        rank.rank = ranking
        ranking += 1
    [rank.save() for rank in ordered]

def compute_event_ranking():
    users = User.objects.filter(is_active=True)
    today = dates.AddDay(datetime.date.today(),-1)
    events = BettableEvent.objects.filter(end_date__gte=today)
    events_ranking = {}
    for event in events:
        LOGGER.info("Working on event " + str(event.name))
        EventRanking.objects.filter(event__id=event.id).delete()
        for user in users:
            LOGGER.info("\tWorking on user " + str(user.username))
            for match in event.matchs.filter(result__isnull=False):
                score = 0
                LOGGER.info("\t\tWorking on match " + str(match.name))
                bet = Bet.objects.filter(match__id=match.id, owner__id=user.id)
                winner = None
                if match.result.first!=match.result.second:
                    winner = match.first if match.result.first>match.result.second else match.second
                LOGGER.info("\t\tWinner is " + str(winner))
                if bet.exists():
                    bet = bet[0]
                    if bet.winner==None and winner==None:
                        score += 3
                        LOGGER.info("\t\tResult: Even found = " + str(score))
                    elif bet.winner!=None and winner!=None:
                        score += 3 if bet.winner.id==winner.id else 0
                        LOGGER.info("\t\tResult: Winner/Looser = " + str(score))
                    score += 1 if bet.result.first==match.result.first else 0
                    LOGGER.info("\t\tResult: First score = " + str(score))
                    score += 1 if bet.result.second==match.result.second else 0
                    LOGGER.info("\t\tResult: Second score = " + str(score))
                    if not events_ranking.has_key(event.id):
                        events_ranking[event.id] = {}
                    if not events_ranking[event.id].has_key(user.id):
                        rank = EventRanking()
                        rank.event = event
                        rank.owner = user
                        rank.overall_score = 0
                        rank.rank = None
                        events_ranking[event.id][user.id] = rank
                        LOGGER.info("\t\tResult: FINAL CREATION = " + str(events_ranking[event.id][user.id].overall_score))
                    events_ranking[event.id][user.id].overall_score += score
                    LOGGER.info("\t\tResult: FINAL score = " + str(events_ranking[event.id][user.id].overall_score))
    for event_id in events_ranking.keys():
        rank_list(events_ranking[event_id].values())

def compute_group_ranking():
    today = dates.AddDay(datetime.date.today(),-1)
    for group in Group.objects.filter(event__end_date__gte=today):
        ranks = []
        for user in list(group.members.all()) + list(group.owners.all()):
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
                LOGGER.warn("User [" + user.id +"] has no rank in event:" + str(group.event.name))
        rank_list(ranks)

def compute_overall_ranking():
    global_scores = EventRanking.objects.values('owner').annotate(global_score = Sum('overall_score'))
    ranks = []
    for entry in global_scores:
        ranking = UserRanking.objects.filter(owner__id=entry['owner'], group=None)
        if ranking.exists():
            ranking = ranking[0]
        else:
            ranking = UserRanking()
            ranking.owner = User.objects.get(id=entry['owner'])
            ranking.group = None
            ranking.overall_score = 0
            ranking.rank = None
            ranking.save()
        ranking.overall_score = entry['global_score']
        ranking.save()
        ranks.append(ranking)
    rank_list(ranks)

class CoreModel(models.Model):

    many_fields = {}
    
    def finalize(self):
        self.save()
        # TODO Loop on many to many only
        for field_name in self._meta.get_all_field_names():
            try:
                if self._meta.get_field(field_name).get_internal_type()=='ManyToManyField':
                    if self.many_fields.has_key(field_name):
                        values = list(self.many_fields[field_name])
                        setattr(self, field_name, values)
            except FieldDoesNotExist:
                None
        self.save()

    def get_editable_fields(self):
        values = []
        for field in self.get_fields():
            if self._meta.get_field(field).get_internal_type()!='ManyToManyField':
                values.append(field)
        return values
        
    def get_associable_field(self):
        values = []
        for field in self.get_fields():
            if self._meta.get_field(field).get_internal_type()=='ManyToManyField':
                values.append(field)
        return values        

    def get_fields(self):
        return []
    
    def get_identifier(self):
        for field in self.get_fields():
            if field=='name':
                return 'name'
        return 'id'
    
    def list_values(self):
        values = []
        for field in self.get_fields():
            LOGGER.debug(self.__class__.__name__ + ' * ' + field)
            if field in self._meta.get_all_field_names():
                if self._meta.get_field(field).get_internal_type()=='ManyToManyField' and getattr(self,field)!=None:
                    values.append(str([e.list_values() for e in list(getattr(self,field).all())]))
                elif self._meta.get_field(field).get_internal_type()=='ForeignKey' and getattr(self,field)!=None:
                    values.append(getattr(self,field).get_value())
                else:
                    values.append(str(getattr(self,field)))
            else:
                # Generic foreign key
                values.append(getattr(self,field).get_value())
        return values
    
    def get_value(self):
        if self.get_identifier()!=None:
            return getattr(self, self.get_identifier())
        else:
            return None
        
    def __unicode__(self):
        return unicode(self.get_value())
    
    def set_attribute(self, source, field_info, string_value):
        try:
            if string_value!='' and string_value!=None:
                if self._meta.get_field(field_info.short_name).get_internal_type()=='ManyToManyField':
                    if not self.many_fields.has_key(field_info.short_name):
                        self.many_fields[field_info.short_name] = []
                    foreign = self._meta.get_field(field_info.short_name).rel.to
                    elements = string_value.split(',')
                    for element in elements:
                        foreign_entity = foreign.retrieve_or_create(source, field_info.name, element)
                        print foreign_entity
                        self.many_fields[field_info.short_name].append(foreign_entity)
                elif self._meta.get_field(field_info.short_name).get_internal_type()=='DateField' or self._meta.get_field(field_info.short_name).get_internal_type()=='DateTimeField':
                    try:
                        dt = datetime.datetime.strptime(string_value,'%m/%d/%Y')
                        if self._meta.get_field(field_info.short_name).get_internal_type()=='DateField':
                            dt = datetime.date(dt.year, dt.month, dt.day)
                    except:
                        dt = string_value # This is not a String???
                    setattr(self, field_info.short_name, dt)
                elif self._meta.get_field(field_info.short_name).get_internal_type()=='ForeignKey':
                    linked_to = self._meta.get_field(field_info.short_name).rel.limit_choices_to
                    foreign = self._meta.get_field(field_info.short_name).rel.to
                    filtering_by_identifier = dict(linked_to)
                    filtering_by_identifier['identifier'] = string_value
                    try:
                        by_identifier = foreign.objects.filter(**filtering_by_identifier)
                    except:
                        by_identifier = None
                    filtering_by_name = dict(linked_to)
                    filtering_by_name['name'] = string_value
                    try:
                        by_name = foreign.objects.filter(**filtering_by_name)
                    except:
                        by_name = None
                    filtering_by_short = dict(linked_to)
                    filtering_by_short['short_name'] = string_value
                    try:
                        by_short = foreign.objects.filter(**filtering_by_short)
                    except:
                        by_short = None
                    if by_identifier!=None and by_identifier.exists():
                        setattr(self, field_info.short_name, by_identifier[0])
                    elif by_name!=None and by_name.exists():
                        setattr(self, field_info.short_name, by_name[0])
                    elif by_short!=None and by_short.exists():
                        setattr(self, field_info.short_name, by_short[0])
                    else:
                        dict_entry = Dictionary.objects.filter(name=linked_to['type'], auto_create=True)
                        if dict_entry.exists():
                            LOGGER.info('Creating new attribute for ' + linked_to['type'] + ' with value ' + string_value)
                            new_attribute = Attributes()
                            new_attribute.active = True
                            new_attribute.identifier = dict_entry[0].identifier + str(string_value.upper()).replace(' ', '_')
                            new_attribute.name = string_value
                            new_attribute.short_name = string_value[0:32]
                            new_attribute.type = linked_to['type']
                            new_attribute.save()
                            setattr(self, field_info.short_name, new_attribute)
                        else:
                            LOGGER.warn('Cannot find foreign key instance on ' + str(self) + '.' + field_info.short_name + ' for value [' + string_value + '] and relation ' + str(linked_to))
                else:
                    setattr(self, field_info.short_name, string_value)
        except FieldDoesNotExist:
            traceback.print_exc()
            LOGGER.error("Wrong security type for " + self.name + ", please check your settings...")
    
    class Meta:
        ordering = ['id']

class Group(CoreModel):
    name = models.CharField(max_length=128)
    owners = models.ManyToManyField(User, related_name='group_owners_rel')
    members = models.ManyToManyField(User, related_name='group_members_rel')
    event = models.ForeignKey('BettableEvent', related_name='group_event')
    
    def get_fields(self):
        return ['name','owners','members', 'event']
    
    class Meta:
        ordering = ['name']

class EventRanking(CoreModel):
    owner = models.ForeignKey(User, related_name='ranking_event_user')
    event = models.ForeignKey('BettableEvent', related_name='ranking_event')
    overall_score = models.IntegerField(default=0)
    rank = models.IntegerField(null=True)
    
    def get_fields(self):
        return ['owner','event','overall_score', 'rank']
    
    class Meta:
        ordering = ['rank']
    
class UserRanking(CoreModel):
    owner = models.ForeignKey(User, related_name='ranking_owner_rel')
    group = models.ForeignKey(Group, related_name='ranking_group_rel', null=True)
    overall_score = models.IntegerField(default=0)
    rank = models.IntegerField(null=True)

    def get_fields(self):
        return ['owner','group','overall_score', 'rank']
    
    class Meta:
        ordering = ['rank']

class Attributes(CoreModel):
    identifier = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    short_name = models.CharField(max_length=32)
    type = models.CharField(max_length=64)
    active = models.BooleanField()
    
    def get_fields(self):
        return ['identifier','name','short_name','type','active']
    
    class Meta:
        ordering = ['name']
        
class Dictionary(CoreModel):
    identifier = models.CharField(max_length=128)
    name = models.CharField(max_length=128)
    auto_create = models.BooleanField()
    
    def get_fields(self):
        return ['identifier','name','auto_create']
    
    class Meta:
        ordering = ['name']
        
class Participant(CoreModel):
    name = models.CharField(max_length=256)
    country = models.ForeignKey(Attributes, limit_choices_to={'type':'country_iso2'}, related_name='participant_country_rel', null=True)
    sport = models.ForeignKey(Attributes, limit_choices_to={'type':'sport'}, related_name='participant_sport_rel', null=True)

    def get_fields(self):
        return super(Participant, self).get_fields() + ['name','country','sport']

    @staticmethod
    def retrieve_or_create(source, key, value):
        translation = Attributes.objects.filter(active=True, name=key, type=source.lower() + '_translation')
        if translation.exists():
            translation = translation[0].short_name
        else:
            translation = key
        participant = Participant.objects.filter(name=value)
        if participant.exists():
            return participant[0]
        else:
            return None

class Score(CoreModel):
    name = models.CharField(max_length=256)
    first = models.IntegerField(default=0)
    second = models.IntegerField(default=0)
    
    def get_fields(self):
        return super(Score, self).get_fields() + ['name', 'first','second']
            
class Match(CoreModel):
    name = models.CharField(max_length=256)
    type = models.ForeignKey(Attributes, limit_choices_to={'type':'match_type'}, related_name='match_type_rel')
    when = models.DateTimeField()
    first = models.ForeignKey(Participant, related_name='match_first_part_rel')
    second = models.ForeignKey(Participant, related_name='match_second_part_rel')
    result = models.ForeignKey(Score, related_name='match_score_rel', null=True)
    
    def get_fields(self):
        return super(Match, self).get_fields() + ['name','type','when','first','second','result']
    
    @staticmethod
    def retrieve_or_create(source, key, value):
        translation = Attributes.objects.filter(active=True, name=key, type=source.lower() + '_translation')
        if translation.exists():
            translation = translation[0].short_name
        else:
            translation = key
        match = Match.objects.filter(name=value)
        if match.exists():
            return match[0]
        else:
            return None

class Bet(CoreModel):
    owner = models.ForeignKey(User, related_name='bet_owner_rel')
    when = models.DateTimeField()
    match = models.ForeignKey(Match, related_name='bet_match_rel')
    winner = models.ForeignKey(Participant, related_name='bet_winner_rel', null=True)
    result = models.ForeignKey(Score, related_name='bet_score_rel')

    def get_fields(self):
        return super(Bet, self).get_fields() + ['owner','when','match','winner','result']
    
class BettableEvent(CoreModel):
    name = models.CharField(max_length=256)
    sport = models.ForeignKey(Attributes, limit_choices_to={'type':'sport'}, related_name='event_sport_rel', null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    participants = models.ManyToManyField(Participant, related_name='event_participant_rel')
    matchs = models.ManyToManyField(Match, related_name='event_match_rel')
    
    def get_fields(self):
        return super(BettableEvent, self).get_fields() + ['name','sport','start_date','end_date','participants','matchs']
    