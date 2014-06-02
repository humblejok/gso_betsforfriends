from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import Q
from django.db.models.fields import FieldDoesNotExist
from django.template import loader
from openpyxl.reader.excel import load_workbook
from seq_common.utils import classes
from datetime import datetime as dt

import datetime
import logging
import os
import traceback
from django.template.context import Context
from gso_betsforfriends.settings import RESOURCES_MAIN_PATH, STATICS_PATH

LOGGER = logging.getLogger(__name__)

def setup():
    populate_attributes_from_xlsx('universe.models.Attributes', os.path.join(RESOURCES_MAIN_PATH,'Repository Setup.xlsx'))
    generate_attributes()

def generate_attributes():
    all_types = Attributes.objects.all().order_by('type').distinct('type')
    for a_type in all_types:
        all_elements = Attributes.objects.filter(type=a_type.type, active=True)
        context = Context({"selection": all_elements})
        template = loader.get_template('rendition/attributes_option_renderer.html')
        rendition = template.render(context)
        # TODO Implement multi-langage
        outfile = os.path.join(STATICS_PATH, a_type.type + '_en.html')
        with open(outfile,'w') as o:
            o.write(rendition.encode('utf-8'))

def populate_attributes_from_xlsx(model_name, xlsx_file):
    model = classes.my_class_import(model_name)
    workbook = load_workbook(xlsx_file)
    sheet = workbook.get_sheet_by_name(name=model.__name__)
    row_index = 0
    # Reading header
    header = []
    for column_index in range(0, sheet.get_highest_column()):
        value = sheet.cell(row = row_index, column=column_index).value
        if value!=None:
            header.append(value if value!='' else header[-1])
        else:
            break
    LOGGER.info('Using header:' + str(header))
    row_index += 1
    while row_index<sheet.get_highest_row():
        if model.objects.filter(identifier=sheet.cell(row = row_index, column=0).value).exists():
            instance = model.objects.get(identifier=sheet.cell(row = row_index, column=0).value)
        else:
            instance = model()
        for i in range(0,len(header)):
            value = sheet.cell(row = row_index, column=i).value
            setattr(instance, header[i], value)
        instance.save()
        row_index += 1

def populate_model_from_xlsx(model_name, xlsx_file):
    LOGGER.info("Loading data in " + model_name)
    model = classes.my_class_import(model_name)
    workbook = load_workbook(xlsx_file)
    sheet = workbook.get_sheet_by_name(name=model.__name__)
    row_index = 0
    # Reading header
    header = []
    for column_index in range(0, sheet.get_highest_column()):
        value = sheet.cell(row = row_index, column=column_index).value
        if value!=None:
            header.append(value if value!='' else header[-1])
        else:
            break
    LOGGER.info('Using header:' + str(header))
    row_index += 1
    while row_index<sheet.get_highest_row():
        instance = model()
        for i in range(0,len(header)):
            value = sheet.cell(row = row_index, column=i).value
            field_info = Attributes()
            field_info.short_name = header[i]
            field_info.name = header[i]
            instance.set_attribute('excel', field_info, value)
        instance.save()
        row_index += 1
        
        
class CoreModel(models.Model):

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
        return 'name'
    
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
                    self.many_fields[field_info.short_name].append(foreign.retrieve_or_create(source, field_info.name, string_value))
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
                    filtering_by_name = dict(linked_to)
                    filtering_by_name['name'] = string_value
                    by_name = foreign.objects.filter(**filtering_by_name)
                    filtering_by_short = dict(linked_to)
                    filtering_by_short['short_name'] = string_value
                    by_short = foreign.objects.filter(**filtering_by_short)
                    if by_name.exists():
                        setattr(self, field_info.short_name, by_name[0])
                    elif by_short.exists():
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
    
class Score(CoreModel):
    first = models.IntegerField()
    second = models.IntegerField()
    
    def get_fields(self):
        return super(Score, self).get_fields() + ['first','second']
            
class Match(CoreModel):
    type = models.ForeignKey(Attributes, limit_choices_to={'type':'match_type'}, related_name='match_type_rel')
    when = models.DateTimeField()
    first = models.ForeignKey(Participant, related_name='first_part_rel')
    second = models.ForeignKey(Participant, related_name='second_part_rel')
    result = models.ManyToManyField(Score, related_name='match_score_rel')
    
    def get_fields(self):
        return super(Match, self).get_fields() + ['when','first','second','result']

