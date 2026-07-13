from datetime import datetime, date
from ..models import (
    DisciplinaryCase, DisciplinaryHearing, DisciplinaryAction,
    DisciplinaryAppeal, Employee,
)


class DisciplineService:
    @staticmethod
    def _resolve(doc_id, model_class):
        if not doc_id:
            return None
        try:
            return model_class.objects.get(pk=doc_id)
        except (model_class.DoesNotExist, ValueError):
            pass
        return model_class.objects.filter(pk=doc_id).first()

    @staticmethod
    def _resolve_employee(emp_ref):
        if not emp_ref:
            return None
        try:
            return Employee.objects.get(pk=emp_ref)
        except (Employee.DoesNotExist, ValueError):
            pass
        return Employee.objects.filter(name=emp_ref).first()

    @staticmethod
    def add_case(data, user):
        doc_id = data.get('doc_id')
        emp = DisciplineService._resolve_employee(data.get('employee'))

        if doc_id:
            case = DisciplineService._resolve(doc_id, DisciplinaryCase)
            if case:
                case.employee = emp or case.employee
                case.incident_date = data.get('incident_date', case.incident_date)
                case.nature_of_offense = data.get('nature_of_offense', case.nature_of_offense)
                case.severity = data.get('severity', case.severity)
                case.description = data.get('description', '')
                case.status = data.get('status', case.status)
                case.resolution = data.get('resolution', '')
                case.resolved_date = data.get('resolved_date') or None
                case.updated_by = user
                case.save()
            return 'updated'

        payload = {
            'employee': emp,
            'incident_date': data.get('incident_date'),
            'nature_of_offense': data.get('nature_of_offense'),
            'severity': data.get('severity', 'Minor'),
            'description': data.get('description', ''),
            'status': data.get('status', 'Open'),
            'resolution': data.get('resolution', ''),
            'resolved_date': data.get('resolved_date') or None,
            'reported_by': user,
            'created_by': user,
            'updated_by': user,
        }
        case = DisciplinaryCase(**payload)
        case.save()
        return 'created'

    @staticmethod
    def add_hearing(data, user):
        case_id = data.get('case_id')
        case = DisciplineService._resolve(case_id, DisciplinaryCase)
        if not case:
            return None

        hearing_id = data.get('doc_id')
        if hearing_id:
            hearing = DisciplineService._resolve(hearing_id, DisciplinaryHearing)
            if hearing:
                hearing.hearing_date = data.get('hearing_date', hearing.hearing_date)
                hearing.panel_members = data.get('panel_members', '')
                hearing.location = data.get('location', '')
                hearing.notes = data.get('notes', '')
                hearing.outcome = data.get('outcome', '')
                hearing.status = data.get('status', hearing.status)
                hearing.save()
            return 'updated'
        else:
            DisciplinaryHearing.objects.create(
                case=case,
                hearing_date=data.get('hearing_date'),
                panel_members=data.get('panel_members', ''),
                location=data.get('location', ''),
                notes=data.get('notes', ''),
                outcome=data.get('outcome', ''),
                status=data.get('status', 'Scheduled'),
            )
            if case.status not in ('Resolved', 'Dismissed'):
                case.status = 'Hearing Scheduled'
                case.save(update_fields=['status'])
            return 'created'

    @staticmethod
    def add_action(data, user):
        case_id = data.get('case_id')
        case = DisciplineService._resolve(case_id, DisciplinaryCase)
        if not case:
            return None

        action_id = data.get('doc_id')
        if action_id:
            action = DisciplineService._resolve(action_id, DisciplinaryAction)
            if action:
                action.action_type = data.get('action_type', action.action_type)
                action.description = data.get('description', '')
                action.issued_date = data.get('issued_date', action.issued_date)
                action.effective_date = data.get('effective_date', action.effective_date)
                action.expiry_date = data.get('expiry_date') or None
                action.supporting_document = data.get('supporting_document', '')
                action.issued_by = user
                action.save()
            return 'updated'
        else:
            DisciplinaryAction.objects.create(
                case=case,
                action_type=data.get('action_type'),
                description=data.get('description', ''),
                issued_date=data.get('issued_date'),
                effective_date=data.get('effective_date'),
                expiry_date=data.get('expiry_date') or None,
                status='Pending',
                issued_by=user,
                supporting_document=data.get('supporting_document', ''),
            )
            return 'created'

    @staticmethod
    def add_appeal(data, user):
        action_id = data.get('action_id')
        action = DisciplineService._resolve(action_id, DisciplinaryAction)
        if not action:
            return None

        DisciplinaryAppeal.objects.create(
            action=action,
            appeal_date=data.get('appeal_date', date.today()),
            grounds=data.get('grounds', ''),
            supporting_evidence=data.get('supporting_evidence', ''),
            status='Submitted',
        )
        action.status = 'Under Appeal'
        action.save(update_fields=['status'])
        return 'created'

    @staticmethod
    def resolve_appeal(appeal_id, decision, data, user):
        appeal = DisciplineService._resolve(appeal_id, DisciplinaryAppeal)
        if not appeal:
            return None

        appeal.status = decision
        appeal.decision_date = data.get('decision_date', date.today())
        appeal.decision_notes = data.get('decision_notes', '')
        appeal.decided_by = user
        appeal.save()

        action = appeal.action
        if action.status == 'Under Appeal':
            action.status = 'Enforced' if decision == 'Upheld' else 'Overturned'
            action.save(update_fields=['status'])
        return decision

    @staticmethod
    def close_case(case_id, resolution, resolved_date, user):
        case = DisciplineService._resolve(case_id, DisciplinaryCase)
        if case:
            case.status = 'Resolved'
            case.resolution = resolution or ''
            case.resolved_date = resolved_date or date.today()
            case.updated_by = user
            case.save(update_fields=['status', 'resolution', 'resolved_date', 'updated_by'])

    @staticmethod
    def get_case_context():
        cases = list(DisciplinaryCase.objects.filter(is_active=True).select_related('employee', 'reported_by').order_by('-created_at'))
        case_data = []
        for c in cases:
            hearings = list(c.hearings.filter(is_active=True).values(
                'pk', 'hearing_date', 'panel_members', 'location', 'notes', 'outcome', 'status',
            ))
            for h in hearings:
                h['id'] = h.pop('pk') or ''

            actions = list(c.actions.filter(is_active=True).values(
                'pk', 'action_type', 'description', 'issued_date', 'effective_date',
                'expiry_date', 'status', 'supporting_document',
            ))
            for a in actions:
                a['id'] = a.pop('pk') or ''

            appeal_list = []
            for a in c.actions.filter(is_active=True):
                for app in a.appeals.filter(is_active=True):
                    appeal_list.append({
                        'id': str(app.pk),
                        'action_id': str(a.pk),
                        'action_type': a.action_type,
                        'appeal_date': str(app.appeal_date),
                        'grounds': app.grounds,
                        'status': app.status,
                        'decision_date': str(app.decision_date) if app.decision_date else '',
                        'decision_notes': app.decision_notes,
                    })

            case_data.append({
                'id': str(c.pk),
                'case_number': c.case_number,
                'employee': c.employee.name if c.employee else '',
                'employee_name': c.employee.name if c.employee else '',
                'incident_date': str(c.incident_date) if c.incident_date else '',
                'nature_of_offense': c.nature_of_offense,
                'severity': c.severity,
                'description': c.description,
                'status': c.status,
                'resolution': c.resolution,
                'resolved_date': str(c.resolved_date) if c.resolved_date else '',
                'hearings': hearings,
                'actions': actions,
                'appeals': appeal_list,
                'created_at': str(c.created_at) if c.created_at else '',
            })

        return {
            'cases': case_data,
            'severity_choices': ['Minor', 'Major', 'Gross'],
            'case_status_choices': ['Open', 'Under Investigation', 'Hearing Scheduled', 'Resolved', 'Dismissed'],
            'action_type_choices': [
                'Verbal Warning', 'Written Warning', 'Final Written Warning',
                'Suspension', 'Pay Cut', 'Demotion', 'Termination', 'Other',
            ],
            'hearing_status_choices': ['Scheduled', 'Completed', 'Postponed', 'Cancelled'],
            'appeal_status_choices': ['Submitted', 'Under Review', 'Upheld', 'Overturned', 'Rejected'],
        }
