# inventory/urls.py
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Main inventory list
    path('', views.InventoryListView.as_view(), name='inventory_list'),
    # OR if you want both:
    # path('api/', views.InventoryListView.as_view(), name='inventory_api'),
    # path('', views.InventoryListView.as_view(), name='inventory_list'),
    path('add-company/', views.add_company, name='add_company'),
    
    # Product CRUD - CORRECTED ORDER (more specific URLs first)
    path('product/add/', views.ProductCreateView.as_view(), name='product_add'),  # This MUST come before <uuid:pk>
    path('product/<uuid:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('product/<uuid:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('product/<uuid:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    
    # Stock History
    path('sku/<uuid:sku_id>/history/', views.stock_history_view, name='stock_history'),
    
    # Language switching
    path('set-language/<str:lang_code>/', views.set_language, name='set_language'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)