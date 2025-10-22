# orders/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.OrderDashboardView.as_view(), name='order_dashboard'),
    
    # Orders
    path('list/', views.OrderListView.as_view(), name='order_list'),
    path('create/', views.OrderCreateView.as_view(), name='order_create'),
    path('<uuid:pk>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<uuid:pk>/edit/', views.OrderUpdateView.as_view(), name='order_edit'),
    path('<uuid:pk>/update-status/', views.update_order_status, name='order_update_status'),
    path('<uuid:pk>/complete/', views.complete_order_and_update_inventory, name='order_complete'),
    
    # Payments
    path('<uuid:pk>/add-payment/', views.add_order_payment, name='order_add_payment'),
    
    # Notifications
    path('<uuid:pk>/preview-notification/', views.preview_notification, name='order_preview_notification'),
    path('<uuid:pk>/send-notification/', views.send_custom_notification, name='order_send_notification'),
    
    # Farmers
    path('farmers/', views.FarmerListView.as_view(), name='farmer_lists'),
    path('farmers/create/', views.FarmerCreateView.as_view(), name='farmer_create'),
    path('farmers/<uuid:pk>/', views.FarmerDetailView.as_view(), name='farmer_detail'),
    path('farmers/<uuid:pk>/edit/', views.FarmerUpdateView.as_view(), name='farmer_edit'),
    
    # API endpoints
    path('api/sku/<uuid:sku_id>/', views.get_sku_details, name='api_sku_details'),
    path('api/farmer/<uuid:farmer_id>/', views.get_farmer_details, name='api_farmer_details'),

     # Inventory Update URLs
    path('inventory/dashboard/', views.inventory_update_dashboard, name='inventory_update_dashboard'),
    path('inventory/product-wise/', views.product_wise_inventory_view, name='product_wise_inventory'),
    path('inventory/bulk-update/', views.bulk_update_inventory, name='bulk_update_inventory'),
    path('inventory/update-single/<uuid:order_id>/', views.update_single_order_inventory, name='update_single_order_inventory'),
    path('inventory/preview-bulk/', views.preview_bulk_update, name='preview_bulk_update'),

]