from django.urls import path
from . import views

app_name = 'hrm'

urlpatterns = [
    path('', views.index, name='index'),
    path('recruitment/', views.recruitment, name='recruitment'),
    path('department/', views.department, name='department'),
    path('employee-database/', views.employee_database, name='employee_database'),
    path('attendance/', views.attendance, name='attendance'),
    path('leave/', views.leave, name='leave'),
    path('payroll/', views.payroll, name='payroll'),
    path('reports/', views.reports, name='reports'),
    path('onboarding/', views.onboarding_offboarding, name='onboarding_offboarding'),
    path('roster/', views.roster_management, name='roster_management'),
    path('expenses/', views.expense_claims, name='expense_claims'),
    path('vault/', views.document_asset_vault, name='document_asset_vault'),
]
