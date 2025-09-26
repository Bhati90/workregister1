from django.contrib import admin
from . import views
from django.urls import path

urlpatterns = [
    path('api/upload-image-to-meta/', views.upload_image_to_meta_api, name='api_upload_image_to_meta'),
    path('api/upload-media-to-meta/', views.upload_media_to_meta_api, name='api_upload_media_to_meta'),
    path('twilio-dial-action/<str:whatsapp_call_id>/', views.twilio_dial_action, name='twilio_dial_action'),
    path('test-twilio/', views.test_twilio_webhook, name='test_twilio_webhook'),
    
    # path('api/templates/', views.get_whatsapp_templates_api, name='get_whatsapp_templates_api'),
    # path('api/flows/save/', views.save_flow_api, name='save_flow_api'),
    path('webhook/', views.whatsapp_webhook_view, name='whatsapp_webhook'),
    # path('api/flows/list/', views.get_flows_list_api, name='api_list_flows'),
    path('api/attributes/', views.attribute_list_create_view, name='attribute-list-create'),
    path('api/attributes/<int:pk>/', views.attribute_detail_view, name='attribute-detail'),
    path('api/initiate-call/', views.initiate_whatsapp_call_view, name='initiate_whatsapp_call'),
    # path('api/get-flow-details/<str:flow_id>/', views.get_flow_details_api_view, name='get_flow_details_api'),

#    path('api/whatsapp-forms/', views.get_whatsapp_forms_api, name='get_whatsapp_forms'),
    path('api/whatsapp-forms/<int:form_id>/', views.flow_form_detail_api, name='flow_form_detail'),
    
    # Webhook endpoints
    # path('webhook/whatsapp/', views.whatsapp_webhook_view, name='whatsapp_webhook'),
    # path('webhook/whatsapp-flows/', views.whatsapp_flow_webhook_view, name='whatsapp_flow_webhook'),
    path('api/save-flow/', views.save_flow_api, name='save_flow'),
    # path('flow-builder/', views.flow_builder_view, name='flow_builder'),
    # 
    #  path('webhook/', views.webhook_verify, name='webhook_verify'),  # GET
    # path('webhook/', views.webhook_handler, name='webhook_handler'),  # POST
    
    # Twilio callback endpoints
    path('twilio-connect/<str:whatsapp_call_id>/', views.twilio_connect_fast, name='twilio_connect'),
    path('twilio-status/<str:whatsapp_call_id>/', views.twilio_status_fast, name='twilio_status'),
    
    # Manual controls
    path('terminate-call/', views.terminate_call, name='terminate_call'),
    # path('webhook/', production_webhook_view, name='whatsapp_webhook'),
    # path('health/', production_health_check, name='health_check'),
    # path('api/flows/<int:flow_id>/update/', views.update_flow, name='update_flow'),
    # # In your urls.py file, add this to urlpatterns:
    # # path('echo/', views.test_echo_endpoint, name='test_echo'),
    # # --- ADD THESE NEW URLS ---
    # path('api/flows/<int:flow_id>/', views.get_flow_detail_api, name='api_get_flow_detail'),
    # path('api/flows/<int:flow_id>/status/', views.update_flow_status_api, name='api_update_flow_status'),
    # path('api/flows/<int:flow_id>/delete/', views.delete_flow_api, name='api_delete_flow'),
    
    path('api/flows/list/', views.get_flows_list_api, name='api_flows_list'),
    path('api/flows/save/', views.save_flow_api, name='api_save_flow'),
    path('api/flows/<int:flow_id>/', views.get_flow_detail_api, name='api_get_flow_detail'),
    path('api/flows/<int:flow_id>/update/', views.update_flow_api, name='api_update_flow'),
    path('api/flows/<int:flow_id>/status/', views.update_flow_status_api, name='api_update_flow_status'),
    path('api/flows/<int:flow_id>/delete/', views.delete_flow_api, name='api_delete_flow'),
    
    # WhatsApp Forms and Templates
    path('api/whatsapp-forms/', views.get_whatsapp_forms_api, name='api_whatsapp_forms'),
    path('api/templates/', views.get_whatsapp_templates_api, name='api_whatsapp_templates'),
    
    # Legacy/Alternative endpoints (if needed for backward compatibility)
    path('get-flow-details/<str:flow_id>/', views.get_flow_detail_api, name='get_flow_details'),
    

]