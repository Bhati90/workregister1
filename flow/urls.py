from django.contrib import admin
from . import views
from django.urls import path

urlpatterns = [
    path('api/get-whatsapp-templates/', views.get_whatsapp_templates_api, name='get_whatsapp_templates_api'),
    path('api/save-flow/', views.save_flow_api, name='save_flow_api'),
]
