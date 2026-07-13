from ..models import KeyPosition, SuccessorCandidate, SuccessionPlan


class SuccessionService:
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
    def add_key_position(data):
        doc_id = data.get('doc_id')
        if doc_id:
            kp = SuccessionService._resolve(doc_id, KeyPosition)
            if kp:
                kp.position_title = data.get('position_title', kp.position_title)
                kp.risk_of_vacancy = data.get('risk_of_vacancy', kp.risk_of_vacancy)
                kp.readiness_gap = data.get('readiness_gap', '')
                kp.status = data.get('status', kp.status)
                kp.save()
            return 'updated'
        else:
            kp = KeyPosition.objects.create(
                position_title=data.get('position_title'),
                risk_of_vacancy=data.get('risk_of_vacancy', 'Medium'),
                readiness_gap=data.get('readiness_gap', ''),
                status=data.get('status', 'Active'),
            )
            return 'created'

    @staticmethod
    def add_successor(data):
        succ_id = data.get('id')
        if succ_id:
            succ = SuccessionService._resolve(succ_id, SuccessorCandidate)
            if succ:
                succ.readiness = data.get('readiness', succ.readiness)
                succ.strengths = data.get('strengths', '')
                succ.development_needs = data.get('development_needs', '')
                succ.is_primary = data.get('is_primary') == 'on'
                succ.save()
            return 'updated'
        else:
            kp_id = data.get('key_position_id')
            emp_id = data.get('employee_id')
            if kp_id and emp_id:
                kp = KeyPosition.objects.filter(pk=kp_id).first()
                if not kp:
                    try:
                        kp = KeyPosition.objects.get(pk=kp_id)
                    except (KeyPosition.DoesNotExist, ValueError):
                        return None
                from ..models import Employee
                try:
                    emp = Employee.objects.get(pk=emp_id)
                except (Employee.DoesNotExist, ValueError):
                    emp = Employee.objects.filter(pk=emp_id).first()
                if not emp:
                    return None
                succ = SuccessorCandidate.objects.create(
                    key_position=kp,
                    employee=emp,
                    readiness=data.get('readiness', '3-5 Years'),
                    strengths=data.get('strengths', ''),
                    development_needs=data.get('development_needs', ''),
                    is_primary=data.get('is_primary') == 'on',
                )
                return 'created'
        return None

    @staticmethod
    def add_plan(data):
        doc_id = data.get('doc_id')
        if doc_id:
            plan = SuccessionService._resolve(doc_id, SuccessionPlan)
            if plan:
                plan.title = data.get('title', plan.title)
                plan.description = data.get('description', '')
                plan.review_date = data.get('review_date') or None
                plan.status = data.get('status', plan.status)
                plan.save()
            return 'updated'
        else:
            plan = SuccessionPlan.objects.create(
                title=data.get('title'),
                description=data.get('description', ''),
                review_date=data.get('review_date') or None,
                status=data.get('status', 'Draft'),
            )
            return 'created'
