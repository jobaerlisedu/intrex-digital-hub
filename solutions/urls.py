from django.urls import path
from . import views

app_name = 'solutions'

urlpatterns = [
    path('', views.index, name='index'),
    path('projects/', views.projects_list, name='projects_list'),
    path('kanban/', views.kanban_board, name='kanban_board'),
    path('sourcing/', views.project_sourcing, name='project_sourcing'),
    path('licenses/', views.licensing_assets, name='licensing_assets'),
    path('stakeholders/', views.client_stakeholders, name='client_stakeholders'),
    path('contacts/', views.global_contacts, name='global_contacts'),
    path('meetings/', views.meeting_scheduler, name='meeting_scheduler'),
]
