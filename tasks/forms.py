from django import forms
from .models import FarmerTaskStatus

class FarmerTaskStatusForm(forms.ModelForm):
    class Meta:
        model = FarmerTaskStatus
        fields = [
            'farmer_crop_cycle',
            'schedule_task',
            'planned_start_date',
            'planned_end_date',
            'actual_completion_date',
            'status',
            'delay_days',
            'delay_reason',
            'delay_date',
        ]
        widgets = {
            'planned_start_date': forms.DateInput(attrs={'type': 'date'}),
            'planned_end_date': forms.DateInput(attrs={'type': 'date'}),
            'actual_completion_date': forms.DateInput(attrs={'type': 'date'}),
            'delay_date': forms.DateInput(attrs={'type': 'date'}),
        }
