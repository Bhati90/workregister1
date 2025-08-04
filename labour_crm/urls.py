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
from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from registration import views as registration_views
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('register/', include('registration.urls')),
     path('', include('pwa.urls')),  
     path('.*/registration-success/', registration_views.success_view, name='registration_success'),

    # A root URL that redirects to the registration home page, or just serves the home page.
    path('', registration_views.home_view, name='root'),

    # A catch-all for development if you have a separate offline page.
    path('offline.html', TemplateView.as_view(template_name='offline.html'), name='offline_page'),
]


if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)