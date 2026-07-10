from django.urls import path
from . import views
from . import reports
from . import portal_views

app_name = 'investment'

urlpatterns = [
    path('', views.index, name='index'),
    path('investors/', views.investor_list, name='investor_list'),
    path('inbound/', views.inbound_list, name='inbound_list'),
    path('loans/', views.loans_list, name='loans_list'),
    path('outbound/', views.outbound_list, name='outbound_list'),
    path('instruments/', views.instruments_list, name='instruments_list'),
    path('pl/', views.pl_list, name='pl_list'),
    path('payables/', views.payables_list, name='payables_list'),
    path('reports/', reports.reports_dashboard, name='reports_dashboard'),
    path('reports/data/<str:report_name>/', reports.report_data_json, name='report_data_json'),
    path('reports/export/<str:report_name>/', reports.export_csv, name='export_csv'),
    path('nav/', views.nav_dashboard, name='nav_dashboard'),
    path('holdings/', views.investor_holdings_list, name='investor_holdings'),
    path('fees/', views.fee_management, name='fee_management'),
    # Investor Portal
    path('portal/login/', portal_views.portal_login, name='portal_login'),
    path('portal/logout/', portal_views.portal_logout, name='portal_logout'),
    path('portal/dashboard/', portal_views.portal_dashboard, name='portal_dashboard'),
    path('portal/statements/', portal_views.portal_statements, name='portal_statements'),
    path('portal/profile/', portal_views.portal_profile, name='portal_profile'),
    path('portal/statement/<str:investor_id>/<str:period>/', portal_views.statement_download, name='statement_download'),
]
