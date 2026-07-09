from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('attendance/', views.attendance, name='attendance'),
    path('roster/', views.roster, name='roster'),
    path('leave/', views.leave, name='leave'),
    path('payslips/', views.payslips, name='payslips'),
    path('advance-salary/', views.advance_salary, name='advance_salary'),
    path('performance/', views.performance, name='performance'),
    path('documents/', views.documents, name='documents'),
    path('training/', views.training_catalog, name='training_catalog'),
    path('development-plans/', views.development_plans, name='development_plans'),
    path('approvals/', views.approvals, name='approvals'),
    path('notifications/', views.notifications, name='notifications'),
    path('succession/', views.succession, name='succession'),
    path('skills/', views.skills_inventory, name='skills_inventory'),
    path('feedback-360/', views.feedback_360, name='feedback_360'),
    path('surveys/', views.surveys, name='surveys'),
    path('compliance-calendar/', views.compliance_calendar, name='compliance_calendar'),
    path('talent-review/', views.talent_review, name='talent_review'),
]
