from django.contrib import admin
from . import views
from django.urls import path

urlpatterns = [
    path('get-whatsapp-templates/', views.get_whatsapp_templates_api, name='get_whatsapp_templates_api'),
    path('save-flow/', views.save_flow_api, name='save_flow_api'),
    path('webhook/', views.whatsapp_webhook_view, name='whatsapp_webhook'),
]
