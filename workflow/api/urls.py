from django.urls import path
from .views import (
    WorkflowInstanceViewSet,
    WorkflowDefinitionViewSet,
    TransitionView,
    AvailableTransitionsView,
)

urlpatterns = [
    path('definitions/', WorkflowDefinitionViewSet.as_view(), name='workflow-definitions'),
    path('instances/', WorkflowInstanceViewSet.as_view(), name='workflow-instances'),
    path('instances/<uuid:instance_id>/transitions/', AvailableTransitionsView.as_view(), name='workflow-transitions'),
    path('instances/<uuid:instance_id>/transition/', TransitionView.as_view(), name='workflow-transition'),
    path('start/', TransitionView.as_view(), name='workflow-start'),
]
