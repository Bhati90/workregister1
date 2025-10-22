from django.urls import path
from . import views
urlpatterns = [
    # Language
    path('set-language/<str:lang_code>/', views.set_language, name='advisory_set_language'),
  
    path('tasks/create/', views.FarmerTaskStatusCreateView.as_view(), name='task_status_create'),
  
 # Task status tracking
    path('tasks/', views.TaskStatusListView.as_view(), name='task_status_list'),
    path('task/<uuid:pk>/complete/',views. CompleteTaskView.as_view(), name='task_complete'),
    path('task/<uuid:pk>/delay/', views.AddDelayView.as_view(), name='task_add_delay'),
    path('task/<uuid:pk>/quick-complete/', views.quick_complete_task, name='task_quick_complete'),
]