# registration/urls.py
from django.urls import path
from . import views
from .dashboard_views import DashboardView,job_create_view,dashboard_login, CategoryDetailView, export_data, dashboard_api

app_name = 'registration'

urlpatterns = [
    # Basic registration URLs
    path('', views.home_view, name='home'),
    path('registration/', views.MultiStepRegistrationView.as_view(), name='registration'),
    path('success/', views.success_view, name='success_page'),
     
    
     path('chat/', views.chat_contact_list_view, name='chat_contact_list'),
    path('template-sender/', views.template_sender_view, name='template_sender'),
    path('api/send-template/', views.send_template_api_view, name='send_template_api'),
#This page will show the detailed conversation for a specific contact
    path('chat/<str:wa_id>/', views.chat_detail_view, name='chat_detail'),
    
    # This is an API endpoint for sending replies from the frontend
    path('api/chat/send-reply/', views.send_reply_api_view, name='send_reply_api'),
    path('whatsapp/webhook/', views.whatsapp_webhook_view, name='whatsapp_webhook'),
    path('api/chat/send-reaction/', views.send_reaction_api_view, name='send_reaction_api'),
    path('api/create-template/', views.create_template_api_view, name='create_template_api'),


    
    path('template-builder/', views.template_builder_view, name='template_builder'),
    # API endpoints
    # path('api/check-mobile-number/', views.check_mobile_number_api, name='check_mobile_number_api'),
    path('api/location-status/', views.location_status_api, name='location_status_api'),
    path('api/submit-registration/', views.submit_registration_api, name='submit_registration_api'),
    
    
    
    # path("dashboard/login/", views.dashboard_login, name="dashboard_login"),
    # Authentication
    path('login/', views.login_view, name='login'),
   
    # path('leader/dashboard/', views.leader_dashboard_view, name='leader_dashboard'),
    path('leader/job/<int:job_id>/find-laborers/', views.find_laborers_view, name='find_laborers_for_job'),
    path('leader/job/<int:job_id>/assign-team/', views.assign_team_to_job_view, name='assign_team_to_job'),
    path('leader/notification/<int:notification_id>/read/', views.mark_notification_read_and_redirect_view, name='read_notification'),
    path('leader/job/<int:job_id>/confirm-start/', views.leader_confirm_start_view, name='leader_confirm_start'),
   path('leader/job/<int:job_id>/cancel-job/', views.leader_cancel_job_view, name='leader_cancel_job'),
    path('leader/dashboard/', views.leader_new_requests_view, name='leader_dashboard'),
    

    path('mukadam/login/', views.mukadam_login_view, name='mukadam_login'),
    path('mukadam/logout/', views.mukadam_logout_view, name='mukadam_logout'),
    path('mukadam/dashboard/', views.mukadam_dashboard_view, name='mukadam_dashboard'),
    path('mukadam/profile/', views.mukadam_profile_view, name='mukadam_profile'),
    path('mukadam/job/<int:job_id>/bid/', views.mukadam_bid_view, name='mukadam_bid'),
    
    
    
    path('bids/live/', views.live_bids_dashboard_view, name='live_bids_dashboard'),
    path('bids/job/<int:job_id>/', views.bid_detail_view, name='bid_detail'),
    path('bids/<int:bid_id>/notify-leader/', views.notify_leader_of_bid_view, name='notify_leader_of_bid'),

    # Add two new paths for the other pages
    path('leader/confirmations/', views.leader_confirmations_view, name='leader_confirmations'),
    path('leader/ongoing-jobs/', views.leader_ongoing_jobs_view, name='leader_ongoing_jobs'),
    path('leader/job/<int:job_id>/manage-team/', views.leader_manage_team_view, name='leader_manage_team'),
    path('leader/bids/', views.leader_bids_view, name='leader_bids'),


    # You'll likely want a generic logout URL
    path('logout/', views.logout_view, name='logout'),
    # path('job/<int:job_id>/complete/', views.mark_job_complete, name='complete_job'),
     path('job/<int:job_id>/live-status/', views.live_job_status_view, name='live_job_status'),

    path('jobs/', views.job_requests_view, name='job_requests'),
    path('job/<int:job_id>/', views.job_detail_view, name='job_detail'), # <-- ADD THIS
    path('job/<int:job_id>/allocate/', views.allocate_job_to_leaders, name='allocate_job'),
    path('job/<int:job_id>/response/', views.view_leader_response_view, name='view_leader_response'),
    path('job/<int:job_id>/approve-team/', views.approve_team_view, name='approve_team'), # <-- ADD THIS
    path('job/<int:job_id>/reject-team/', views.reject_team_view, name='reject_team'),   # <-- ADD THIS
    # path('job/<int:job_id>/complete/', views.mark_job_complete, name='mark_job_complete'),
    path('job/<int:job_id>/live-status/', views.live_job_status_view, name='live_job_status'),
     path('job/create/', views.job_create_view, name='create_job'), 
  
  
    # Leader Portal
    #  path('leader/respond-job/<int:job_id>/', views.respond_to_job_api, name='respond_to_job'),
   path('leader/assignment/<int:assignment_id>/update-status/', views.update_worker_status_view, name='update_worker_status'),
   path('leader/assignment/<int:assignment_id>/request-help/', views.request_help_view, name='request_help'),# registration/urls.py
   path('admin/help-request/<int:request_id>/resolve/', views.resolve_help_request_view, name='resolve_help_request'),
# ... (inside your urlpatterns list) ...
   path('job/<int:job_id>/advanced-search/', views.advanced_labor_search_view, name='advanced_labor_search'),
   
   path('leader/job/<int:job_id>/confirm-start/', views.leader_confirm_start_view, name='leader_confirm_start'),
   path('leader/job/<int:job_id>/cancel-job/', views.leader_cancel_job_view, name='leader_cancel_job'),
    
    # Notifications
    # path('notification/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),

    path('profile/leader/<int:user_id>/', views.leader_profile_view, name='leader_profile'),
    path('profile/mukadam/<int:mukadam_id>/', views.mukadam_performance_profile_view, name='mukadam_profile'),
    path('profile/labourer/<int:labourer_id>/', views.labourer_profile_view, name='labourer_profile'),
    path('profiles/select/', views.profile_selector_view, name='profile_selector'),
    

    # Dashboard URLs
    path('dashboard/login', dashboard_login, name='dashboard'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('dashboard/category/<str:category>/', CategoryDetailView.as_view(), name='category_detail'),
    path('dashboard/export/', export_data, name='export_all'),
    path('dashboard/export/<str:category>/', export_data, name='export_category'),
    path('dashboard/api/', dashboard_api, name='dashboard_api'),

    # Direct step access
    path('step1/', views.MultiStepRegistrationView.as_view(), {'step': '1'}, name='step1'),
    path('step2/', views.MultiStepRegistrationView.as_view(), {'step': '2'}, name='step2'),
    path('step3/', views.MultiStepRegistrationView.as_view(), {'step': '3'}, name='step3'),
]