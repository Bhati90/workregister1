from django.urls import path
from . import views

urlpatterns = [
    # Farmer management
    path('farmers/', views.FarmerListView.as_view(), name='farmer_list'),
    path('farmers/<uuid:pk>/', views.FarmerDetailView.as_view(), name='farmer_detail'),
    
    
   
    
    # Language
    path('set-language/<str:lang_code>/', views.set_language, name='advisory_set_language'),
]