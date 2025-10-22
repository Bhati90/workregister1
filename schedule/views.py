# advisory/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView
from django.db.models import Q, Count, Prefetch, F, Case, When, Value, CharField
from django.utils import timezone
from recommandations.models import Crop
from datetime import datetime, timedelta
from .models import (
    Farmer
)
from cropcycle.models import FarmerCropCycle
from tasks.models import FarmerTaskStatus

class FarmerListView(ListView):
    """List all farmers with filtering"""
    model = Farmer
    template_name = 'farmer_list.html'
    context_object_name = 'farmers'
    paginate_by = 20

    def get_queryset(self):
        queryset = Farmer.objects.annotate(
            active_cycles_count=Count('crop_cycles'),
            pending_tasks_count=Count(
                'crop_cycles__task_statuses',
                filter=Q(crop_cycles__task_statuses__status='PENDING')
            ),
            overdue_tasks_count=Count(
                'crop_cycles__task_statuses',
                filter=Q(crop_cycles__task_statuses__status='OVERDUE')
            )
        )

        # Search by name or phone
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone_number__icontains=search)
            )

        # Filter by crop
        crop = self.request.GET.get('crop')
        if crop:
            queryset = queryset.filter(crop_cycles__crop_variety__crop_id=crop)

        # Filter by task status
        task_status = self.request.GET.get('task_status')
        if task_status:
            queryset = queryset.filter(crop_cycles__task_statuses__status=task_status)

        return queryset.distinct().order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        context['crops'] = Crop.objects.all()
        context['status_choices'] = FarmerTaskStatus.StatusChoices.choices
        
        # Statistics
        context['total_farmers'] = Farmer.objects.count()
        context['active_cycles'] = FarmerCropCycle.objects.count()
        context['pending_tasks'] = FarmerTaskStatus.objects.filter(status='PENDING').count()
        context['overdue_tasks'] = FarmerTaskStatus.objects.filter(status='OVERDUE').count()
        
        return context
class FarmerDetailView(DetailView):
    """Detailed view of a farmer with all crop cycles and tasks"""
    model = Farmer
    template_name = 'farmer_detail.html'
    context_object_name = 'farmer'

    def get_queryset(self):
        return Farmer.objects.prefetch_related(
            Prefetch('crop_cycles', 
                queryset=FarmerCropCycle.objects.select_related(
                    'crop_variety__crop', 'schedule'
                ).prefetch_related(
                    Prefetch('task_statuses',
                        queryset=FarmerTaskStatus.objects.select_related(
                            'schedule_task'
                        ).prefetch_related('schedule_task__products')
                    )
                )
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        
        # **ADD THIS: Calculate task statistics**
        farmer = self.object
        
        # Get all tasks across all crop cycles for this farmer
        all_tasks = FarmerTaskStatus.objects.filter(
            farmer_crop_cycle__farmer=farmer
        )
        
        context['completed_tasks_count'] = all_tasks.filter(status='COMPLETED').count()
        context['pending_tasks_count'] = all_tasks.filter(status='PENDING').count()
        context['overdue_tasks_count'] = all_tasks.filter(status='OVERDUE').count()
        context['total_tasks_count'] = all_tasks.count()
        
        return context

def set_language(request, lang_code):
    """Set language preference"""
    if lang_code in ['en', 'mr']:
        request.session['language'] = lang_code
    return redirect(request.META.get('HTTP_REFERER', 'farmer_list'))
