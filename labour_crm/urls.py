"""
URL configuration for labour_crm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# labour_crm/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # All URLs from 'registration.urls' will be prefixed with 'register/'
    path('register/whatsapp/', include('flow.urls')),
    path('register/order/', include('order.urls')),
    path('register/summery/',include('summery.urls')),
    path('register/inventory/', include('inventory.urls')),
    path('register/task/', include('tasks.urls')),
    path('register/crop/', include('cropcycle.urls')),
    path('register/recom/', include('recommandations.urls')),
    path('register/schedule/', include('schedule.urls')),
    path('', include('pwa.urls')), # PWA URLs at the root level
    path('register/api/analytics/', include('analytics.urls')), # <-- Add this line

  
]

# Serve static and media files in development
if settings.DEBUG:
    # This line is for your CSS, JS, and project images
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # This line is for user-uploaded files like Whats
    # App images
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)