"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
import logging

urls_logger = logging.getLogger('config.urls')

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from config import views as config_views
from config.exceptions import handler400, handler403, handler404, handler500


handler400 = 'config.exceptions.handler400'
handler403 = 'config.exceptions.handler403'
handler404 = 'config.exceptions.handler404'
handler500 = 'config.exceptions.handler500'

urlpatterns = [
    path('health/', config_views.health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('erp/', config_views.erp_dashboard, name='erp_dashboard'),
    path('', include('frontend.urls', namespace='frontend')),
    path('hrm/', include('hrm.urls', namespace='hrm')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
    path('investment/', include('investment.urls', namespace='investment')),
    path('solutions/', include('solutions.urls', namespace='solutions')),
    path('training/', include('training.urls', namespace='training')),
    path('billing/', include('billing.urls', namespace='billing')),
    path('users/', include('accounts.urls', namespace='accounts')),

    # REST API v1
    path('api/v1/', include('config.api')),

    # Documentation
    path('docs/', config_views.documentation_viewer, name='docs_index'),
    path('docs/<path:path>/', config_views.documentation_viewer, name='docs_page'),

    # JWT Authentication API (mobile / 3rd-party)
    path('api/v1/auth/', include('accounts.auth.urls')),

    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

# Serve media files in development
from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
