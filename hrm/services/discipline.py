from datetime import datetime
from config.firebase import db
from google.cloud.firestore import SERVER_TIMESTAMP


class DisciplineService:
    COLLECTION = 'hrm_disciplinary_cases'
    APPEALS_COLLECTION = 'hrm_disciplinary_appeals'

    @staticmethod
    def _next_case_number():
        from google.cloud.firestore_v1 import transactional
        counter_ref = db.collection('hrm_counters').document('disciplinary')

        @transactional
        def increment(transaction):
            snap = list(transaction.get(counter_ref))[0]
            if not snap.exists:
                transaction.set(counter_ref, {'sequence': 1})
                return f"DC-{datetime.now().year}-0001"
            seq = snap.to_dict()['sequence'] + 1
            transaction.update(counter_ref, {'sequence': seq})
            return f"DC-{datetime.now().year}-{seq:04d}"

        return increment(db.transaction())

    @staticmethod
    def add_case(data, user):
        doc_id = data.get('doc_id')
        now = datetime.now().isoformat()
        payload = {
            'employee': data.get('employee'),
            'incident_date': data.get('incident_date'),
            'nature_of_offense': data.get('nature_of_offense'),
            'severity': data.get('severity', 'Minor'),
            'description': data.get('description', ''),
            'status': data.get('status', 'Open'),
            'resolution': data.get('resolution', ''),
            'resolved_date': data.get('resolved_date') or None,
            'updated_at': now,
            'updated_by': f'users/{user.id}',
        }
        if doc_id:
            db.collection(DisciplineService.COLLECTION).document(doc_id).update(payload)
            return 'updated'
        payload['case_number'] = DisciplineService._next_case_number()
        payload['reported_by'] = f'users/{user.id}'
        payload['hearings'] = []
        payload['actions'] = []
        payload['is_active'] = True
        payload['created_at'] = now
        payload['created_by'] = f'users/{user.id}'
        doc_ref = db.collection(DisciplineService.COLLECTION).document()
        doc_ref.set(payload)
        return 'created'

    @staticmethod
    def add_hearing(data, user):
        case_id = data.get('case_id')
        if not case_id:
            return None
        import time
        hearing = {
            'id': f'h_{int(time.time())}',
            'hearing_date': data.get('hearing_date'),
            'panel_members': data.get('panel_members', ''),
            'location': data.get('location', ''),
            'notes': data.get('notes', ''),
            'outcome': data.get('outcome', ''),
            'status': data.get('status', 'Scheduled'),
        }
        case_ref = db.collection(DisciplineService.COLLECTION).document(case_id)
        case = case_ref.get()
        if not case.exists:
            return None
        existing = case.to_dict().get('hearings', [])
        existing.append(hearing)
        case_ref.update({
            'hearings': existing,
            'status': 'Hearing Scheduled',
            'updated_at': datetime.now().isoformat(),
            'updated_by': f'users/{user.id}',
        })
        return 'created'

    @staticmethod
    def add_action(data, user):
        case_id = data.get('case_id')
        if not case_id:
            return None
        import time
        action = {
            'id': f'a_{int(time.time())}',
            'action_type': data.get('action_type'),
            'description': data.get('description', ''),
            'issued_date': data.get('issued_date'),
            'effective_date': data.get('effective_date'),
            'expiry_date': data.get('expiry_date') or None,
            'status': 'Pending',
            'issued_by': f'users/{user.id}',
            'supporting_document': data.get('supporting_document', ''),
        }
        case_ref = db.collection(DisciplineService.COLLECTION).document(case_id)
        case = case_ref.get()
        if not case.exists:
            return None
        existing = case.to_dict().get('actions', [])
        existing.append(action)
        case_ref.update({
            'actions': existing,
            'updated_at': datetime.now().isoformat(),
            'updated_by': f'users/{user.id}',
        })
        return 'created'

    @staticmethod
    def add_appeal(data, user):
        action_id = data.get('action_id')
        if not action_id:
            return None
        case_ref = db.collection(DisciplineService.COLLECTION).document(action_id)
        case = case_ref.get()
        if not case.exists:
            return None
        cdata = case.to_dict()
        doc_ref = db.collection(DisciplineService.APPEALS_COLLECTION).document()
        doc_ref.set({
            'action_id': action_id,
            'case_number': cdata.get('case_number', ''),
            'employee_name': cdata.get('employee_name', ''),
            'appeal_date': data.get('appeal_date'),
            'grounds': data.get('grounds'),
            'supporting_evidence': data.get('supporting_evidence', ''),
            'status': 'Submitted',
            'decision_date': None,
            'decision_notes': '',
            'decided_by': None,
            'is_active': True,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
        })
        actions = cdata.get('actions', [])
        for a in actions:
            if a.get('id') and a['status'] not in ('Enforced', 'Overturned'):
                a['status'] = 'Under Appeal'
        case_ref.update({
            'actions': actions,
            'updated_at': datetime.now().isoformat(),
        })
        return 'created'

    @staticmethod
    def resolve_appeal(appeal_id, decision, data, user):
        now = datetime.now().isoformat()
        appeal_ref = db.collection(DisciplineService.APPEALS_COLLECTION).document(appeal_id)
        appeal = appeal_ref.get()
        if not appeal.exists:
            return None
        adata = appeal.to_dict()
        adata['status'] = decision
        adata['decision_date'] = data.get('decision_date', datetime.now().strftime('%Y-%m-%d'))
        adata['decision_notes'] = data.get('decision_notes', '')
        adata['decided_by'] = f'users/{user.id}'
        adata['updated_at'] = now
        appeal_ref.update(adata)

        action_id = adata.get('action_id')
        if action_id:
            case_ref = db.collection(DisciplineService.COLLECTION).document(action_id)
            case = case_ref.get()
            if case.exists:
                cdata = case.to_dict()
                actions = cdata.get('actions', [])
                for a in actions:
                    if a.get('status') == 'Under Appeal':
                        a['status'] = 'Enforced' if decision == 'Upheld' else 'Overturned'
                case_ref.update({'actions': actions, 'updated_at': now})
        return decision

    @staticmethod
    def close_case(case_id, resolution, resolved_date, user):
        db.collection(DisciplineService.COLLECTION).document(case_id).update({
            'status': 'Resolved',
            'resolution': resolution or '',
            'resolved_date': resolved_date or datetime.now().strftime('%Y-%m-%d'),
            'updated_at': datetime.now().isoformat(),
            'updated_by': f'users/{user.id}',
        })

    @staticmethod
    def get_case_context():
        cases = sorted(
            [{'id': d.id, **d.to_dict()} for d in db.collection(DisciplineService.COLLECTION).stream()
             if d.to_dict().get('is_active')],
            key=lambda c: c.get('created_at', '') or '',
            reverse=True,
        )
        appeals = sorted(
            [{'id': d.id, **d.to_dict()} for d in db.collection(DisciplineService.APPEALS_COLLECTION).stream()
             if d.to_dict().get('is_active')],
            key=lambda a: a.get('appeal_date', '') or '',
            reverse=True,
        )
        return {
            'cases': cases,
            'hearings': [h for c in cases for h in c.get('hearings', [])],
            'actions': [a for c in cases for a in c.get('actions', [])],
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
