from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from workflow.models import WorkflowDefinition, WorkflowInstance
from workflow.services import (
    start_workflow,
    transition,
    get_instance,
    get_available_transitions,
)


class WorkflowDefinitionViewSet(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        module = request.query_params.get('module')
        entity_type = request.query_params.get('entity_type')
        qs = WorkflowDefinition.objects.filter(is_active=True)
        if module:
            qs = qs.filter(module=module)
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        data = [
            {
                'id': str(w.id),
                'name': w.name,
                'module': w.module,
                'entity_type': w.entity_type,
                'description': w.description,
            }
            for w in qs
        ]
        return Response(data)


class WorkflowInstanceViewSet(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        module = request.query_params.get('module')
        entity_id = request.query_params.get('entity_id')
        qs = WorkflowInstance.objects.filter(is_active=True)
        if module:
            qs = qs.filter(workflow__module=module)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        data = []
        for inst in qs.select_related('workflow', 'current_state'):
            state = inst.current_state
            data.append({
                'id': str(inst.id),
                'workflow': inst.workflow.name,
                'entity_id': inst.entity_id,
                'entity_label': inst.entity_label,
                'current_state': state.state_key if state else None,
                'current_state_label': state.label if state else None,
                'is_active': inst.is_active,
                'started_at': inst.started_at.isoformat() if inst.started_at else None,
            })
        return Response(data)

    def post(self, request):
        module = request.data.get('module')
        entity_type = request.data.get('entity_type')
        entity_id = request.data.get('entity_id')
        if not all([module, entity_type, entity_id]):
            return Response({'error': 'module, entity_type, and entity_id required'}, status=400)
        instance = start_workflow(
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_label=request.data.get('entity_label', ''),
            context=request.data.get('context'),
            user=request.user,
        )
        if not instance:
            return Response({'error': 'Could not start workflow'}, status=400)
        return Response({'id': str(instance.id), 'status': 'started'}, status=201)


class AvailableTransitionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, instance_id):
        instance = WorkflowInstance.objects.filter(id=instance_id, is_active=True).first()
        if not instance:
            return Response({'error': 'Instance not found'}, status=404)
        transitions = get_available_transitions(instance, user=request.user)
        return Response({'transitions': transitions})


class TransitionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, instance_id=None):
        if not instance_id:
            return Response({'error': 'instance_id required'}, status=400)
        trigger = request.data.get('trigger')
        comment = request.data.get('comment', '')
        if not trigger:
            return Response({'error': 'trigger required'}, status=400)
        instance = WorkflowInstance.objects.filter(id=instance_id, is_active=True).first()
        if not instance:
            return Response({'error': 'Instance not found'}, status=404)
        success, error = transition(instance, trigger, user=request.user, comment=comment)
        if not success:
            return Response({'error': error}, status=400)
        state = instance.current_state
        return Response({
            'status': 'transitioned',
            'current_state': state.state_key if state else None,
            'current_state_label': state.label if state else None,
            'is_active': instance.is_active,
        })
