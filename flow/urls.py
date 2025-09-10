from django.contrib import admin
from . import views
from django.urls import path

urlpatterns = [
    path('api/templates/', views.get_whatsapp_templates_api, name='get_whatsapp_templates_api'),
    path('api/flows/save/', views.save_flow_api, name='save_flow_api'),
    path('webhook/', views.whatsapp_webhook_view, name='whatsapp_webhook'),
    # path('upload-template-media/', views.upload_media_to_meta ),
    # path('api/flows/list/', views.get_flows_list_api, name='api_list_flows'),
]