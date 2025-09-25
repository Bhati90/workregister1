from django.contrib import admin
from . import views
from django.urls import path

urlpatterns = [
     path('form-builder/', views.whatsapp_form_builder_view, name='whatsapp_form_builder'),
    path('submit-form-and-template/', views.submit_form_and_template_view, name='submit_form_and_template'),
    # Add to your urlpatterns
     path('send-flow/', views.send_flow_view, name='send_flow_view'),

    path('api/send-flow-template/', views.send_flow_template_api_view, name='send_flow_template'),
    path('api/send-interactive-flow/', views.send_interactive_flow_message, name='send_interactive_flow'),
    path('api/get-flow-templates/', views.get_flow_templates, name='get_flow_templates'),
]