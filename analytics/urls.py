from django.urls import path
from . import views
from .views import auto_analyze_farmers_view, get_segment_details_view

urlpatterns = [
    # Converts English to SQL
    path('generate-query/', views.generate_query_view, name='generate-query'),
    path('api/auto-analyze-farmers/', auto_analyze_farmers_view),
    path('api/segment-details/', get_segment_details_view),
    # Executes the generated SQL
    path('execute-query/', views.execute_query_view, name='execute-query'),
]

