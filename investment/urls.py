from django.urls import path
from . import views
from . import reports

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
]
