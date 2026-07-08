from django.db import transaction
from .models import Project, ProjectPhase, Task, ProjectRequisition


def create_project_with_phases(data, phases_data, user):
    with transaction.atomic():
        project = Project.objects.create(
            name=data['name'],
            client_name=data.get('client_name', ''),
            total_budget=data.get('total_budget', 0),
            start_date=data['start_date'],
            end_date=data['end_date'],
            status='Planning',
            created_by=user,
        )
        for phase in phases_data:
            ProjectPhase.objects.create(
                project=project,
                phase_name=phase['name'],
                budget_allocation=phase.get('budget', 0),
                start_date=phase['start_date'],
                end_date=phase['end_date'],
                status='Pending',
            )
    return project


def get_project_budget_status(project):
    total_allocated = sum(p.budget_allocation for p in project.phases.all())
    total_used = sum(r.estimated_cost for r in project.requisitions.filter(status='Approved'))
    return {
        'budget': project.total_budget,
        'allocated': total_allocated,
        'used': total_used,
        'remaining': project.total_budget - total_used,
    }
