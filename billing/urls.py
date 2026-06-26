from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.index, name='index'),
    path('coa/', views.chart_of_accounts, name='chart_of_accounts'),
    path('journal/', views.general_journal, name='general_journal'),
    path('invoices/', views.ar_invoices, name='ar_invoices'),
    path('bills/', views.ap_bills, name='ap_bills'),
    path('tax/', views.tax_center, name='tax_center'),
    path('reports/', views.financial_statements, name='financial_statements'),
    path('audit/', views.audit_trail, name='audit_trail'),
]
