from django import forms
from django.forms import ModelForm
from django.forms.models import BaseModelFormSet
from events2.models import *
from datetime import datetime
from events2.helpers import get_academic_years


class StudentBatchForm(forms.ModelForm):
  year = forms.ChoiceField(choices = get_academic_years())
  csv_file = forms.FileField(required = True)
  class Meta:
    model = StudentBatch
    exclude = ['academic', 'stcount', 'organiser']

  def clean(self):
    file_types = {
      'csv': 'text/csv',
    }
    component = ''
    if 'csv_file' in self.cleaned_data:
      component = self.cleaned_data['csv_file']
      if not component.content_type in file_types['csv']:
        self._errors["csv_file"] = self.error_class(["Not a valid file format."])
    return
  #def __init__(self, *args, **kwargs):
  #  user = kwargs.pop('user')
  #  super(StudentBatchForm, self).__init__(*args, **kwargs)
  #  self.fields['academic'].queryset = AcademicCenter.objects.filter(pk=user.organiser.academic.id)


class NewStudentBatchForm(forms.ModelForm):
  csv_file = forms.FileField(required = True)

  class Meta:
    model = StudentBatch
    exclude = ['academic', 'year', 'department', 'stcount', 'organiser']

  def clean(self):
    file_types = {
      'csv': 'text/csv',
    }
    component = ''
    if 'csv_file' in self.cleaned_data:
      component = self.cleaned_data['csv_file']
      if not component.content_type in file_types['csv']:
        self._errors["csv_file"] = self.error_class(["Not a valid file format."])
    return

class TrainingRequestForm(forms.ModelForm):
  course_type = forms.ChoiceField(choices=[('', '---------'), (0, 'Software Course outside lab hours'), (1, 'Software Course mapped in lab hours'), (2, ' Software Course unmapped in lab hours')])
  course = forms.ModelChoiceField(empty_label='---------', queryset=CourseMap.objects.none())
  batch = forms.ModelChoiceField(empty_label='---------', queryset=StudentBatch.objects.none())
  training_planner = forms.CharField()
  class Meta:
    model = TrainingRequest
    exclude = ['participants', 'status', 'training_planner']

  def clean(self):
    tp = TrainingPlanner.objects.get(pk=self.cleaned_data['training_planner'])
    if self.cleaned_data and 'department' in self.cleaned_data and self.cleaned_data['department']:
      if tp.is_full(self.cleaned_data['department']):
        raise forms.ValidationError("No. of training requests for this department exceeded.")

    if 'course_type' in self.cleaned_data and self.cleaned_data['course_type'] and 'department' in self.cleaned_data and self.cleaned_data['department']:
      if tp.is_course_full(self.cleaned_data['course_type'], self.cleaned_data['department']):
        raise forms.ValidationError("No. of training requests for selected course type exceeded")
    
    # Date restriction
    if self.cleaned_data and 'sem_start_date' in self.cleaned_data and self.cleaned_data['sem_start_date']:
      start_date, end_date =tp.get_current_semester_date_duration()
      print tp.id, '-------------------'
      print start_date, end_date, self.cleaned_data['sem_start_date']
      if not (self.cleaned_data['sem_start_date'] <= end_date and self.cleaned_data['sem_start_date'] >= start_date):
        raise forms.ValidationError("Invalid semester start date")
    return self.cleaned_data
  
  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    super(TrainingRequestForm, self).__init__(*args, **kwargs)
    
    if kwargs and 'data' in kwargs:
      # Generating course list based on course type
      if 'course_type' in kwargs['data'] and kwargs['data']['course_type'] != '':
        courses = CourseMap.objects.filter(category=kwargs['data']['course_type'])
        choices = [('', '---------'),]
        for course in courses:
          choices.append((course.id, course.course_name()))
        self.fields['course'].queryset = CourseMap.objects.filter(category=kwargs['data']['course_type'])
        self.fields['course'].choices = choices
        self.fields['course'].initial = kwargs['data']['course']
      # Generating students batch list based on department
      if kwargs['data']['department'] != '':
        department = kwargs['data']['department']
        self.fields['batch'].queryset = StudentBatch.objects.filter(academic_id=user.organiser.academic.id, stcount__gt=0, department_id=department)
        self.fields['batch'].initial =  kwargs['data']['batch']

class TrainingRequestEditForm(forms.ModelForm):
  course_type = forms.ChoiceField(choices=[('', '---------'), (0, 'Software Course outside lab hours'), (1, 'Software Course mapped in lab hours'), (2, ' Software Course unmapped in lab hours')])
  course = forms.ModelChoiceField(empty_label='---------', queryset=CourseMap.objects.none())
  training_planner = forms.CharField()
  class Meta:
    model = TrainingRequest
    exclude = ['participants', 'status', 'training_planner', 'department', 'batch']
  
  def clean(self):
    # Date restriction
    if self.cleaned_data and 'sem_start_date' in self.cleaned_data and self.cleaned_data['sem_start_date']:
      tp = TrainingPlanner.objects.get(pk=self.cleaned_data['training_planner'])
      start_date, end_date =tp.get_current_semester_date_duration()
      print start_date, end_date, self.cleaned_data['sem_start_date']
      if not (self.cleaned_data['sem_start_date'] <= end_date and self.cleaned_data['sem_start_date'] >= start_date):
        raise forms.ValidationError("Invalid semester start date")
    return self.cleaned_data

  def __init__(self, *args, **kwargs):
    training = kwargs.pop('training', None)
    user = kwargs.pop('user', None)
    super(TrainingRequestEditForm, self).__init__(*args, **kwargs)
    
    if training:
      self.fields['sem_start_date'].initial = training.sem_start_date
      self.fields['course_type'].initial = training.course.category
      self.fields['course'].queryset = CourseMap.objects.filter(category=training.course.category)
      self.fields['course'].initial = training.course_id
