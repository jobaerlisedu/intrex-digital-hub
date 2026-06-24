from django.urls import path
from . import views

app_name = 'training'

urlpatterns = [
    path('', views.index, name='index'),
    path('overview/', views.overview, name='overview'),
    path('inquiries/', views.inquiries, name='inquiries'),
    path('employee-database/', views.employee_database, name='employee_database'),
    path('trainer-database/', views.trainer_database, name='trainer_database'),
    path('contact-directory/', views.contact_directory, name='contact_directory'),
    path('brand-ambassadors/', views.brand_ambassadors, name='brand_ambassadors'),
    path('course-creation/', views.course_creation, name='course_creation'),
    path('batch-management/', views.batch_management, name='batch_management'),
    path('class-calendar/', views.class_calendar, name='class_calendar'),
    path('student-list/', views.student_list, name='student_list'),
    path('installment-plan/', views.installment_plan, name='installment_plan'),
    path('revenue-tracker/', views.revenue_tracker, name='revenue_tracker'),
    path('expense-tracker/', views.expense_tracker, name='expense_tracker'),
    path('sales-management/', views.sales_management, name='sales_management'),
    path('course-assessments/', views.course_assessments, name='course_assessments'),
    path('certificates/', views.certificates, name='certificates'),
    path('job-placement/', views.job_placement, name='job_placement'),
    path('reports/', views.reports, name='reports'),
    path('system-audit-logs/', views.system_audit_logs, name='system_audit_logs'),
]
