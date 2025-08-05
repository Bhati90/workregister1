# registration/urls.py
from django.urls import path
from . import views
from .dashboard_views import DashboardView, CategoryDetailView, export_data, dashboard_api

app_name = 'registration'

urlpatterns = [
    
    path('', views.home_view, name='home'),
    path('registration/', views.MultiStepRegistrationView.as_view(), name='registration'),
    path('success/', views.success_view, name='success_page'),

    # The crucial API endpoint for PWA submission
    path('api/submit-registration/', views.submit_registration_api, name='submit_registration_api'), # This remains as /api/submit-registration/ relative to 'register/'
    #  path('api/check-phone-number/', views.check_phone_number_api, name='check_phone_number_api'),
    # path('api/submit-registration/', views.submit_registr
    # Dashboard URLs (existing)
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/category/<str:category>/', CategoryDetailView.as_view(), name='category_detail'),
    path('dashboard/export/', export_data, name='export_all'),
    path('dashboard/export/<str:category>/', export_data, name='export_category'),
    path('dashboard/api/', dashboard_api, name='dashboard_api'),

    # Direct step access (optional, for development/testing)
    path('step1/', views.MultiStepRegistrationView.as_view(), {'step': '1'}, name='step1'),
    path('step2/', views.MultiStepRegistrationView.as_view(), {'step': '2'}, name='step2'),
    path('step3/', views.MultiStepRegistrationView.as_view(), {'step': '3'}, name='step3'),
]