from django.utils import timezone
from ..models import DisciplinaryCase, DisciplinaryHearing, DisciplinaryAction, DisciplinaryAppeal


class DisciplineService:
    @staticmethod
    def add_case(data, user):
        doc_id = data.get('doc_id')
        if doc_id:
            case = DisciplinaryCase.objects.get(id=doc_id)
            case.employee_id = data.get('employee')
            case.incident_date = data.get('incident_date')
            case.nature_of_offense = data.get('nature_of_offense')
            case.severity = data.get('severity', 'Minor')
            case.description = data.get('description', '')
            case.status = data.get('status', 'Open')
            case.resolution = data.get('resolution', '')
            case.resolved_date = data.get('resolved_date') or None
            case.updated_by = user
            case.save()
            return 'updated'
        else:
            DisciplinaryCase.objects.create(
                employee_id=data.get('employee'),
                incident_date=data.get('incident_date'),
                nature_of_offense=data.get('nature_of_offense'),
                severity=data.get('severity', 'Minor'),
                description=data.get('description', ''),
                status=data.get('status', 'Open'),
                reported_by=user,
                created_by=user,
            )
            return 'created'

    @staticmethod
    def add_hearing(data, user):
        case_id = data.get('case_id')
        if not case_id:
            return None
        doc_id = data.get('doc_id')
        if doc_id:
            hearing = DisciplinaryHearing.objects.get(id=doc_id)
            hearing.hearing_date = data.get('hearing_date')
            hearing.panel_members = data.get('panel_members', '')
            hearing.location = data.get('location', '')
            hearing.notes = data.get('notes', '')
            hearing.outcome = data.get('outcome', '')
            hearing.status = data.get('status', 'Scheduled')
            hearing.save()
            return 'updated'
        else:
            DisciplinaryHearing.objects.create(
                case_id=case_id,
                hearing_date=data.get('hearing_date'),
                panel_members=data.get('panel_members', ''),
                location=data.get('location', ''),
                notes=data.get('notes', ''),
                status=data.get('status', 'Scheduled'),
            )
            DisciplinaryCase.objects.filter(id=case_id).update(status='Hearing Scheduled')
            return 'created'

    @staticmethod
    def add_action(data, user):
        case_id = data.get('case_id')
        if not case_id:
            return None
        doc_id = data.get('doc_id')
        if doc_id:
            action = DisciplinaryAction.objects.get(id=doc_id)
            action.action_type = data.get('action_type')
            action.description = data.get('description', '')
            action.issued_date = data.get('issued_date')
            action.effective_date = data.get('effective_date')
            action.expiry_date = data.get('expiry_date') or None
            action.status = data.get('status', 'Pending')
            action.save()
            return 'updated'
        else:
            DisciplinaryAction.objects.create(
                case_id=case_id,
                action_type=data.get('action_type'),
                description=data.get('description', ''),
                issued_date=data.get('issued_date'),
                effective_date=data.get('effective_date'),
                expiry_date=data.get('expiry_date') or None,
                issued_by=user,
            )
            return 'created'

    @staticmethod
    def add_appeal(data, user):
        action_id = data.get('action_id')
        if not action_id:
            return None
        DisciplinaryAppeal.objects.create(
            action_id=action_id,
            appeal_date=data.get('appeal_date'),
            grounds=data.get('grounds'),
            supporting_evidence=data.get('supporting_evidence', ''),
        )
        DisciplinaryAction.objects.filter(id=action_id).update(status='Under Appeal')
        return 'created'

    @staticmethod
    def resolve_appeal(appeal_id, decision, data, user):
        appeal = DisciplinaryAppeal.objects.get(id=appeal_id)
        appeal.status = decision
        appeal.decision_date = data.get('decision_date', timezone.now().date())
        appeal.decision_notes = data.get('decision_notes', '')
        appeal.decided_by = user
        appeal.save()

        action = appeal.action
        if decision == 'Overturned':
            action.status = 'Overturned'
        elif decision == 'Upheld':
            action.status = 'Enforced'
        action.save()
        return decision

    @staticmethod
    def close_case(case_id, resolution, resolved_date, user):
        DisciplinaryCase.objects.filter(id=case_id).update(
            status='Resolved',
            resolution=resolution,
            resolved_date=resolved_date or timezone.now().date(),
            updated_by=user,
        )

    @staticmethod
    def get_case_context():
        cases = DisciplinaryCase.objects.filter(is_active=True).select_related('employee', 'reported_by')
        hearings = DisciplinaryHearing.objects.filter(is_active=True).select_related('case')
        actions = DisciplinaryAction.objects.filter(is_active=True).select_related('case', 'issued_by')
        appeals = DisciplinaryAppeal.objects.filter(is_active=True).select_related('action', 'decided_by')

        return {
            'cases': cases,
            'hearings': hearings,
            'actions': actions,
            'appeals': appeals,
            'severity_choices': ['Minor', 'Major', 'Gross'],
            'case_status_choices': ['Open', 'Under Investigation', 'Hearing Scheduled', 'Resolved', 'Dismissed'],
            'action_type_choices': [
                'Verbal Warning', 'Written Warning', 'Final Written Warning',
                'Suspension', 'Pay Cut', 'Demotion', 'Termination', 'Other',
            ],
            'hearing_status_choices': ['Scheduled', 'Completed', 'Postponed', 'Cancelled'],
            'appeal_status_choices': ['Submitted', 'Under Review', 'Upheld', 'Overturned', 'Rejected'],
        }
