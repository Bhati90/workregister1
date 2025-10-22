from django.shortcuts import render
from django.views.generic import ListView
from django.db.models import Q, Count, F
from django.shortcuts import redirect
from .models import FarmerCropCycle, CropVariety,Schedule,ScheduleTask, TaskProduct
from recommandations.models import Crop
from schedule.models import Farmer
from django.utils import timezone
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from .forms import ScheduleForm, ScheduleTaskForm, TaskProductForm
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from .forms import FarmerCropCycleForm

class FarmerCropCycleCreateView(CreateView):
    model = FarmerCropCycle
    form_class = FarmerCropCycleForm
    template_name = 'crop_cycle_create.html'
    success_url = reverse_lazy('crop_cycle_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        return context

class ScheduleCreateView(CreateView):
    model = Schedule
    form_class = ScheduleForm
    template_name = 'schedule_create.html'
    success_url = reverse_lazy('farmer_list')  # Match your desired route

class ScheduleTaskCreateView(CreateView):
    model = ScheduleTask
    form_class = ScheduleTaskForm
    template_name = 'schedule_task_create.html'
    success_url = reverse_lazy('schedule_task_list')

class TaskProductCreateView(CreateView):
    model = TaskProduct
    form_class = TaskProductForm
    template_name = 'task_product_create.html'
    success_url = reverse_lazy('task_product_list')

# Create your views here.

class CropCycleListView(ListView):
    """List all crop cycles with advanced filtering"""
    model = FarmerCropCycle
    template_name = 'crop_cycle_list.html'
    context_object_name = 'crop_cycles'
    paginate_by = 20

    def get_queryset(self):
        queryset = FarmerCropCycle.objects.select_related(
            'farmer', 'crop_variety__crop', 'schedule'
        ).annotate(
            total_tasks=Count('task_statuses'),
            completed_tasks=Count('task_statuses', filter=Q(task_statuses__status='COMPLETED')),
            pending_tasks=Count('task_statuses', filter=Q(task_statuses__status='PENDING')),
            overdue_tasks=Count('task_statuses', filter=Q(task_statuses__status='OVERDUE')),
            days_since_sowing=F('sowing_date')
        )

        # Filter by farmer
        farmer = self.request.GET.get('farmer')
        if farmer:
            queryset = queryset.filter(farmer_id=farmer)

        # Filter by crop
        crop = self.request.GET.get('crop')
        if crop:
            queryset = queryset.filter(crop_variety__crop_id=crop)

        # Filter by variety
        variety = self.request.GET.get('variety')
        if variety:
            queryset = queryset.filter(crop_variety_id=variety)

        # Filter by schedule
        schedule = self.request.GET.get('schedule')
        if schedule:
            queryset = queryset.filter(schedule_id=schedule)

        # Filter by date range
        sowing_from = self.request.GET.get('sowing_from')
        sowing_to = self.request.GET.get('sowing_to')
        if sowing_from:
            queryset = queryset.filter(sowing_date__gte=sowing_from)
        if sowing_to:
            queryset = queryset.filter(sowing_date__lte=sowing_to)

        # Filter by completion status
        completion_status = self.request.GET.get('completion_status')
        if completion_status == 'completed':
            queryset = queryset.filter(pending_tasks=0, overdue_tasks=0)
        elif completion_status == 'in_progress':
            queryset = queryset.filter(pending_tasks__gt=0)
        elif completion_status == 'has_overdue':
            queryset = queryset.filter(overdue_tasks__gt=0)

        sort = self.request.GET.get('sort', '-sowing_date')
        return queryset.order_by(sort)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        
        # Filter options
        context['farmers'] = Farmer.objects.all().order_by('name')
        context['crops'] = Crop.objects.all().order_by('name')
        context['varieties'] = CropVariety.objects.select_related('crop').order_by('name')
        context['schedules'] = Schedule.objects.all().order_by('name')
        
        # Preserve filters
        context['filters'] = {
            'farmer': self.request.GET.get('farmer', ''),
            'crop': self.request.GET.get('crop', ''),
            'variety': self.request.GET.get('variety', ''),
            'schedule': self.request.GET.get('schedule', ''),
            'sowing_from': self.request.GET.get('sowing_from', ''),
            'sowing_to': self.request.GET.get('sowing_to', ''),
            'completion_status': self.request.GET.get('completion_status', ''),
            'sort': self.request.GET.get('sort', '-sowing_date'),
        }
        
        return context


def set_language(request, lang_code):
    """Set language preference"""
    if lang_code in ['en', 'mr']:
        request.session['language'] = lang_code
    return redirect(request.META.get('HTTP_REFERER', 'farmer_list'))
