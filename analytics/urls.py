from django.urls import path
from . import views

urlpatterns = [
    # Converts English to SQL
    path('generate-query/', views.generate_query_view, name='generate-query'),
    # Executes the generated SQL
    path('execute-query/', views.execute_query_view, name='execute-query'),
]

