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
import sys
import logging

urls_logger = logging.getLogger('config.urls')

# Run database migrations and bootstrap admin on server startup
if not any(arg in sys.argv for arg in ['makemigrations', 'migrate', 'collectstatic', 'check', 'shell', 'test']):
    try:
        from config.bootstrap import run_startup
        run_startup()
    except Exception as e:
        urls_logger.exception("Django Startup Error")

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from config import views as config_views

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
    path('portal-login/', config_views.PortalLoginView.as_view(), name='portal_login'),
    path('portal/', include('portal.urls')),
]
