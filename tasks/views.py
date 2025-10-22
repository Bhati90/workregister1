from django.shortcuts import render

# Create your views here.

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import UpdateView
from django.urls import reverse
from datetime import timedelta

from .models import FarmerTaskStatus
  # Import the model
from schedule.models import Farmer
from recommandations.models import Crop
from cropcycle.models import ScheduleTask, FarmerCropCycle
from django.views.generic import ListView
from django.db.models import Q, Count, Prefetch, F, Case, When, Value, CharField
from django.utils import timezone
from django.urls import reverse_lazy
from .forms import FarmerTaskStatusForm
from django.views.generic.edit import CreateView

class FarmerTaskStatusCreateView(CreateView):
    model = FarmerTaskStatus
    form_class = FarmerTaskStatusForm
    template_name = 'task_status_create.html'
    success_url = reverse_lazy('task_status_list')  # You can choose where to redirect
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        return context
def set_language(request, lang_code):
    """Set language preference"""
    if lang_code in ['en', 'mr']:
        request.session['language'] = lang_code
    return redirect(request.META.get('HTTP_REFERER', 'farmer_list'))

class TaskStatusListView(ListView):
    """List all task statuses with filtering"""
    model = FarmerTaskStatus
    template_name = 'task_status_list.html'
    context_object_name = 'task_statuses'
    paginate_by = 50

    def get_queryset(self):
        queryset = FarmerTaskStatus.objects.select_related(
            'farmer_crop_cycle__farmer',
            'farmer_crop_cycle__crop_variety__crop',
            'schedule_task__schedule'
        ).prefetch_related('schedule_task__products')

        # Filter by farmer
        farmer = self.request.GET.get('farmer')
        if farmer:
            queryset = queryset.filter(farmer_crop_cycle__farmer_id=farmer)

        # Filter by crop
        crop = self.request.GET.get('crop')
        if crop:
            queryset = queryset.filter(farmer_crop_cycle__crop_variety__crop_id=crop)

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Filter by stage
        stage = self.request.GET.get('stage')
        if stage:
            queryset = queryset.filter(schedule_task__stage_name__icontains=stage)

        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(planned_start_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(planned_end_date__lte=date_to)

        # Filter upcoming tasks (next 7 days)
        upcoming = self.request.GET.get('upcoming')
        if upcoming:
            today = timezone.now().date()
            next_week = today + timedelta(days=7)
            queryset = queryset.filter(
                planned_start_date__gte=today,
                planned_start_date__lte=next_week,
                status='PENDING'
            )

        # Filter overdue tasks
        show_overdue = self.request.GET.get('show_overdue')
        if show_overdue:
            queryset = queryset.filter(status='OVERDUE')

        sort = self.request.GET.get('sort', 'planned_start_date')
        return queryset.order_by(sort)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        
        # Filter options
        context['farmers'] = Farmer.objects.all().order_by('name')
        context['crops'] = Crop.objects.all().order_by('name')
        context['status_choices'] = FarmerTaskStatus.StatusChoices.choices
        
        # Get unique stages
        context['stages'] = ScheduleTask.objects.values_list(
            'stage_name', flat=True
        ).distinct().order_by('stage_name')
        
        # **ADD THIS: Calculate status counts from the filtered queryset**
        # Get the full filtered queryset (not paginated)
        full_queryset = self.get_queryset()
        context['completed_count'] = full_queryset.filter(status='COMPLETED').count()
        context['overdue_count'] = full_queryset.filter(status='OVERDUE').count()
        context['pending_count'] = full_queryset.filter(status='PENDING').count()
        context['in_progress_count'] = full_queryset.filter(status='IN_PROGRESS').count()
        
        # Preserve filters
        context['filters'] = {
            'farmer': self.request.GET.get('farmer', ''),
            'crop': self.request.GET.get('crop', ''),
            'status': self.request.GET.get('status', ''),
            'stage': self.request.GET.get('stage', ''),
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'upcoming': self.request.GET.get('upcoming', ''),
            'show_overdue': self.request.GET.get('show_overdue', ''),
            'sort': self.request.GET.get('sort', 'planned_start_date'),
        }
        
        return context

class CompleteTaskView(UpdateView):
    """Mark a task as complete"""
    model = FarmerTaskStatus
    fields = ['actual_completion_date']
    template_name = 'task_complete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        return context
    
    def form_valid(self, form):
        task = form.save(commit=False)
        completion_date = form.cleaned_data.get('actual_completion_date') or timezone.now().date()
        task.mark_complete(completion_date)
        
        messages.success(
            self.request,
            'Task marked as completed successfully!' if self.request.session.get('language', 'en') == 'en'
            else 'कार्य यशस्वीरित्या पूर्ण झाले!'
        )
        
        return redirect('farmer_detail', pk=task.farmer_crop_cycle.farmer.id)
    
    def get_success_url(self):
        return reverse('farmer_detail', kwargs={'pk': self.object.farmer_crop_cycle.farmer.id})


class AddDelayView(UpdateView):
    """Add delay to a specific task"""
    model = FarmerTaskStatus
    fields = ['delay_days', 'delay_reason']
    template_name = 'task_add_delay.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_language'] = self.request.session.get('language', 'en')
        return context
    
    def form_valid(self, form):
        task = form.save(commit=False)
        delay_days = form.cleaned_data['delay_days']
        delay_reason = form.cleaned_data.get('delay_reason')
        
        task.add_delay(delay_days, delay_reason)
        
        messages.success(
            self.request,
            f'Delay of {delay_days} days added successfully!' if self.request.session.get('language', 'en') == 'en'
            else f'{delay_days} दिवसांचा विलंब यशस्वीरित्या जोडला गेला!'
        )
        
        return redirect('farmer_detail', pk=task.farmer_crop_cycle.farmer.id)
    
    def get_success_url(self):
        return reverse('farmer_detail', kwargs={'pk': self.object.farmer_crop_cycle.farmer.id})


def quick_complete_task(request, pk):
    """Quick complete task without form"""
    task = get_object_or_404(FarmerTaskStatus, pk=pk)
    
    if request.method == 'POST':
        task.mark_complete()
        
        messages.success(
            request,
            'Task completed successfully!' if request.session.get('language', 'en') == 'en'
            else 'कार्य यशस्वीरित्या पूर्ण झाले!'
        )
    
    return redirect('farmer_detail', pk=task.farmer_crop_cycle.farmer.id)