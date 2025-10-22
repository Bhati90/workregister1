from django.urls import path
from . import views

urlpatterns = [
   # Language
    path('set-language/<str:lang_code>/', views.set_language, name='advisory_set_language'),
    path('demand-analysis/', views.ProductDemandAnalysisView.as_view(), name='product_demand_analysis'),
    
    # Product recommendations
    path('recommendations/', views.ProductRecommendationView.as_view(), name='product_recommendations'),
]