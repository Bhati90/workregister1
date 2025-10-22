from django.urls import path
from . import views

# app_name = 'summary'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Daily Summaries
    path('daily/', views.daily_summary_list, name='daily_summary_list'),
    path('daily/<str:date>/', views.daily_summary_detail, name='daily_summary_detail'),
    
    # Performance Metrics
    path('performance/', views.performance_metrics, name='performance_metrics'),
    
    # Growth Metrics
    path('growth/', views.growth_metrics, name='growth_metrics'),
    
    # Geographic Performance
    path('geographic/', views.geographic_performance, name='geographic_performance'),
    path('geographic/<uuid:pk>/', views.geographic_detail, name='geographic_detail'),
    
    # Alerts
    path('alerts/', views.alert_list, name='alert_list'),
    path('alerts/<uuid:pk>/', views.alert_detail, name='alert_detail'),
    path('alerts/<uuid:pk>/acknowledge/', views.alert_acknowledge, name='alert_acknowledge'),
    path('alerts/<uuid:pk>/resolve/', views.alert_resolve, name='alert_resolve'),
    path('alerts/<uuid:pk>/dismiss/', views.alert_dismiss, name='alert_dismiss'),
    
    # Anomalies
    path('anomalies/', views.anomaly_list, name='anomaly_list'),
    path('anomalies/<uuid:pk>/', views.anomaly_detail, name='anomaly_detail'),
    
    # Trends
    path('trends/', views.trend_analysis, name='trend_analysis'),
    path('trends/<uuid:pk>/', views.trend_detail, name='trend_detail'),
    
    # Benchmarks
    path('benchmarks/', views.benchmark_comparison, name='benchmark_comparison'),
    path('benchmarks/<uuid:pk>/', views.benchmark_detail, name='benchmark_detail'),
    
    # API Endpoints
    path('api/daily-summary/', views.api_daily_summary, name='api_daily_summary'),
    path('api/alerts-summary/', views.api_alerts_summary, name='api_alerts_summary'),
]