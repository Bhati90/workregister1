from django import forms
from .models import FarmerCropCycle

class FarmerCropCycleForm(forms.ModelForm):
    class Meta:
        model = FarmerCropCycle
        fields = [
            'farmer',
            'crop_variety',
            'schedule',
            'sowing_date',
            'is_active',
            # Add any other fields you want exposed
        ]
        widgets = {
            'sowing_date': forms.DateInput(attrs={'type': 'date'}),
        }

from django import forms
from .models import Schedule, ScheduleTask, TaskProduct

class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ['crop_variety', 'name', 'season']

class ScheduleTaskForm(forms.ModelForm):
    class Meta:
        model = ScheduleTask
        fields = [
            'schedule', 'stage_name', 'start_day', 'end_day',
            'application_type', 'purpose_and_benefits', 'products'
        ]
        widgets = {
            'products': forms.SelectMultiple(attrs={'size': 8}),
        }

class TaskProductForm(forms.ModelForm):
    class Meta:
        model = TaskProduct
        fields = [
            'task', 'product', 'dosage_amount', 'dosage_unit',
            'dosage_per_area', 'dosage_area_unit'
        ]
