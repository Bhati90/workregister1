# your_project_root/registration/urls.py

from django.urls import path
from . import views
from .dashboard_views import DashboardView, CategoryDetailView, export_data, dashboard_api

app_name = 'registration'

urlpatterns = [
    # Home page (existing)
    path('', views.home_view, name='home'),

    # Multi-step registration (existing)
    path('registration/', views.MultiStepRegistrationView.as_view(), name='registration'),
     path('/registration-success/', views.success_view, name='registration_success'),
    path('api/submit-registration/', views.submit_registration_api, name='submit_registration_api'),
   
    # Success page (MODIFIED NAME FOR CONSISTENCY WITH JS REDIRECT)
    # path('success/', views.success_view, name='success_page'), # Changed name='success' to name='success_page'

    # Dashboard URLs (existing)
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/category/<str:category>/', CategoryDetailView.as_view(), name='category_detail'),
    path('dashboard/export/', export_data, name='export_all'),
    path('dashboard/export/<str:category>/', export_data, name='export_category'),
    path('dashboard/api/', dashboard_api, name='dashboard_api'),

    # Direct step access (optional, for development/testing - existing)
    path('step1/', views.MultiStepRegistrationView.as_view(), {'step': '1'}, name='step1'),
    path('step2/', views.MultiStepRegistrationView.as_view(), {'step': '2'}, name='step2'),
    path('step3/', views.MultiStepRegistrationView.as_view(), {'step': '3'}, name='step3'),

    # NEW: API endpoint for offline registration submissions
    # path('api/registration/submit/', views.submit_final_registration_api, name='api_registration_submit'), # <--- ADD THIS LINE
]