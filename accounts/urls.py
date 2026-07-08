from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('',                        views.user_list,          name='user_list'),
    path('create/',                 views.user_create,        name='user_create'),
    path('<int:user_id>/edit/',     views.user_edit,          name='user_edit'),
    path('<int:user_id>/toggle/',   views.user_toggle_active, name='user_toggle_active'),
    path('audit-logs/',             views.audit_logs,         name='audit_logs'),
    path('sync-users/',             views.sync_users_view,    name='sync_users'),
    path('sessions/<int:session_id>/revoke/', views.revoke_session, name='revoke_session'),
]
