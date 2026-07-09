from django.urls import path
from . import views
from . import portal_views
from . import analytics_views

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

    # Employee Self-Service Portal
    path('portal/', portal_views.dashboard, name='portal_dashboard'),
    path('portal/profile/', portal_views.profile, name='portal_profile'),
    path('portal/attendance/', portal_views.attendance, name='portal_attendance'),
    path('portal/leave/', portal_views.leave, name='portal_leave'),
    path('portal/payslips/', portal_views.payslips, name='portal_payslips'),
    path('portal/performance/', portal_views.performance, name='portal_performance'),
    path('portal/documents/', portal_views.documents, name='portal_documents'),
    path('portal/training/', portal_views.training_catalog, name='portal_training_catalog'),
    path('portal/development-plans/', portal_views.development_plans, name='portal_development_plans'),
    path('portal/notifications/', portal_views.notifications, name='portal_notifications'),
    path('portal/succession/', portal_views.succession, name='portal_succession'),

    # Analytics
    path('analytics/', analytics_views.dashboard, name='analytics_dashboard'),
    path('analytics/workforce/', analytics_views.workforce, name='analytics_workforce'),
    path('analytics/training/', analytics_views.training, name='analytics_training'),

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

    # Phase 5: Portal Views
    path('portal/skills/', portal_views.skills_inventory, name='portal_skills_inventory'),
    path('portal/feedback-360/', portal_views.feedback_360, name='portal_feedback_360'),
    path('portal/surveys/', portal_views.surveys, name='portal_surveys'),
    path('portal/compliance-calendar/', portal_views.compliance_calendar, name='portal_compliance_calendar'),
    path('portal/talent-review/', portal_views.talent_review, name='portal_talent_review'),
]
