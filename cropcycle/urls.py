from django.urls import path
from . import views

urlpatterns = [
# Crop cycles
     path('schedules/create/', views.ScheduleCreateView.as_view(), name='schedule_create'),
    path('schedule-tasks/create/', views.ScheduleTaskCreateView.as_view(), name='schedule_task_create'),
    path('task-products/create/', views.TaskProductCreateView.as_view(), name='task_product_create'),
    path('crop-cycles/create/', views.FarmerCropCycleCreateView.as_view(), name='crop_cycle_create'),

    path('crop-cycles/', views.CropCycleListView.as_view(), name='crop_cycle_list'),
     # Language
    path('set-language/<str:lang_code>/', views.set_language, name='advisory_set_language'),
]