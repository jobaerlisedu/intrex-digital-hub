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
    path('payroll/get-payslip/', views.get_payslip, name='get_payslip'),
    path('reports/', views.reports, name='reports'),
    path('onboarding/', views.onboarding_offboarding, name='onboarding_offboarding'),
    path('roster/', views.roster_management, name='roster_management'),
    path('expenses/', views.expense_claims, name='expense_claims'),
    path('vault/', views.document_asset_vault, name='document_asset_vault'),
    path('performance/', views.performance, name='performance'),
    path('disciplinary/', views.disciplinary, name='disciplinary'),

    # Notifications & Succession
    path('notifications/', views.notification_center, name='notification_center'),
    path('succession/', views.succession_planning, name='succession_planning'),
    path('notifications/unread-count/', views.get_unread_notification_count, name='unread_notification_count'),

    # Phase 5: Admin Views
    path('skills-inventory/', views.skills_inventory, name='skills_inventory'),
    path('feedback-360/', views.feedback_360, name='feedback_360'),
    path('surveys/', views.engagement_surveys, name='engagement_surveys'),
    path('compliance-calendar/', views.compliance_calendar, name='compliance_calendar'),
    path('talent-review/', views.talent_review, name='talent_review'),
    path('settings/', views.hrm_settings, name='hrm_settings'),
    path('employee-cases/<str:emp_id>/', views.employee_cases_json, name='employee_cases_json'),
]
