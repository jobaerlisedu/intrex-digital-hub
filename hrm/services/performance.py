from .base import ORMService
from ..models import ReviewCycle, KPI, PerformanceReview, PerformanceImprovementPlan, Employee


class PerformanceService(ORMService):
    model = ReviewCycle

    @staticmethod
    def _resolve(doc_id, model_class):
        if not doc_id:
            return None
        try:
            return model_class.objects.get(pk=doc_id)
        except (model_class.DoesNotExist, ValueError):
            pass
        return model_class.objects.filter(pk=doc_id).first()

    @classmethod
    def add_review_cycle(cls, data, user):
        doc_id = data.get('doc_id')
        if doc_id:
            instance = cls._resolve(doc_id, ReviewCycle)
            if instance:
                instance.name = data.get('name', instance.name)
                instance.start_date = data.get('start_date', instance.start_date)
                instance.end_date = data.get('end_date', instance.end_date)
                instance.review_type = data.get('review_type', instance.review_type)
                instance.status = data.get('status', instance.status)
                instance.updated_by = user
                instance.save()
            return 'updated'
        else:
            ReviewCycle.objects.create(
                name=data.get('name'),
                start_date=data.get('start_date'),
                end_date=data.get('end_date'),
                review_type=data.get('review_type', 'Half-Yearly'),
                status=data.get('status', 'Draft'),
                created_by=user,
                updated_by=user,
            )
            return 'created'

    @classmethod
    def add_kpi(cls, data, user):
        doc_id = data.get('doc_id')
        if doc_id:
            instance = cls._resolve(doc_id, KPI)
            if instance:
                instance.name = data.get('name', instance.name)
                instance.description = data.get('description', '')
                instance.unit = data.get('unit', '')
                instance.target_value = data.get('target_value') or None
                instance.default_weight = data.get('default_weight', 1.0)
                instance.updated_by = user
                instance.save()
            return 'updated'
        else:
            KPI.objects.create(
                name=data.get('name'),
                description=data.get('description', ''),
                unit=data.get('unit', ''),
                target_value=data.get('target_value') or None,
                default_weight=data.get('default_weight', 1.0),
                created_by=user,
                updated_by=user,
            )
            return 'created'

    @classmethod
    def add_review(cls, data, user):
        doc_id = data.get('doc_id')
        emp_id = data.get('employee')
        reviewer_id = data.get('reviewer')
        cycle_name = data.get('review_cycle')

        emp = Employee.objects.filter(name=emp_id).first() if emp_id else None
        reviewer = Employee.objects.filter(name=reviewer_id).first() if reviewer_id else None
        cycle = ReviewCycle.objects.filter(name=cycle_name).first() if cycle_name else None

        if doc_id:
            instance = cls._resolve(doc_id, PerformanceReview)
            if instance:
                instance.employee = emp or instance.employee
                instance.reviewer = reviewer or instance.reviewer
                instance.review_cycle = cycle or instance.review_cycle
                instance.overall_score = data.get('overall_score') or None
                instance.strengths = data.get('strengths', '')
                instance.improvements = data.get('improvements', '')
                instance.goals = data.get('goals', '')
                instance.status = data.get('status', instance.status)
                instance.updated_by = user
                instance.save()
            return 'updated'
        else:
            PerformanceReview.objects.create(
                employee=emp,
                reviewer=reviewer,
                review_cycle=cycle,
                overall_score=data.get('overall_score') or None,
                strengths=data.get('strengths', ''),
                improvements=data.get('improvements', ''),
                goals=data.get('goals', ''),
                status=data.get('status', 'Self-Assessment'),
                created_by=user,
                updated_by=user,
            )
            return 'created'

    @classmethod
    def add_pip(cls, data, user):
        doc_id = data.get('doc_id')
        emp_name = data.get('employee')
        emp = Employee.objects.filter(name=emp_name).first() if emp_name else None

        if doc_id:
            instance = cls._resolve(doc_id, PerformanceImprovementPlan)
            if instance:
                instance.employee = emp or instance.employee
                instance.issue_description = data.get('issue_description', '')
                instance.improvement_goals = data.get('improvement_goals', '')
                instance.start_date = data.get('start_date', instance.start_date)
                instance.end_date = data.get('end_date', instance.end_date)
                instance.status = data.get('status', instance.status)
                instance.updated_by = user
                instance.save()
            return 'updated'
        else:
            PerformanceImprovementPlan.objects.create(
                employee=emp,
                issue_description=data.get('issue_description', ''),
                improvement_goals=data.get('improvement_goals', ''),
                start_date=data.get('start_date'),
                end_date=data.get('end_date'),
                status=data.get('status', 'Open'),
                created_by=user,
                updated_by=user,
            )
            return 'created'

    @classmethod
    def delete_record(cls, action, doc_id):
        model_map = {
            'delete_review_cycle': ReviewCycle,
            'delete_kpi': KPI,
            'delete_review': PerformanceReview,
            'delete_pip': PerformanceImprovementPlan,
        }
        mc = model_map.get(action)
        if mc:
            instance = cls._resolve(doc_id, mc)
            if instance:
                instance.is_active = False
                instance.save(update_fields=['is_active'])
