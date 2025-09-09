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
from registration import views as registration_views # Import your views
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    # All URLs from 'registration.urls' will be prefixed with 'register/'
    path('register/', include('registration.urls', namespace='registration')), # Added namespace
    path('register/whatsapp/', include('flow.urls')),
    path('', include('pwa.urls')), # PWA URLs at the root level

    # A root URL that redirects to the registration home page.
    # Be careful with conflicts here. This will match before pwa.urls if ordered higher.
    # For now, keep it, but understand it might conflict with PWA's root handling.
    # The PWA START_URL is /register/registration/, so this root path might be for general site landing.
    path('', registration_views.home_view, name='root'),
    # A catch-all for development if you have a separate offline page.
    path('offline.html', TemplateView.as_view(template_name='offline.html'), name='offline_page'),
]

# Serve static and media files in development
if settings.DEBUG:
    # This line is for your CSS, JS, and project images
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # This line is for user-uploaded files like WhatsApp images
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)