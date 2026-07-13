from ..models import EmployeeEducation, EmployeeExperience, EmployeeSkill, CompetencyRating, Employee, Competency


def _now_date():
    from datetime import date
    return str(date.today())


class SkillsService:
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
    def _resolve_employee(emp_id):
        if not emp_id:
            return None
        try:
            return Employee.objects.get(pk=emp_id)
        except (Employee.DoesNotExist, ValueError):
            pass
        return Employee.objects.filter(pk=emp_id).first()

    @staticmethod
    def add_education(data):
        emp = SkillsService._resolve_employee(data.get('employee_id'))
        if not emp:
            return None
        doc_id = data.get('doc_id')
        if doc_id:
            edu = SkillsService._resolve(doc_id, EmployeeEducation)
            if edu:
                edu.degree = data.get('degree', edu.degree)
                edu.institution = data.get('institution', edu.institution)
                edu.field_of_study = data.get('field_of_study', '')
                edu.start_year = data.get('start_year') or None
                edu.end_year = data.get('end_year') or None
                edu.grade = data.get('grade', '')
                edu.save()
            return 'updated'
        EmployeeEducation.objects.create(
            employee=emp,
            degree=data.get('degree'),
            institution=data.get('institution'),
            field_of_study=data.get('field_of_study', ''),
            start_year=data.get('start_year') or None,
            end_year=data.get('end_year') or None,
            grade=data.get('grade', ''),
        )
        return 'created'

    @staticmethod
    def add_experience(data):
        emp = SkillsService._resolve_employee(data.get('employee_id'))
        if not emp:
            return None
        doc_id = data.get('doc_id')
        if doc_id:
            exp = SkillsService._resolve(doc_id, EmployeeExperience)
            if exp:
                exp.company = data.get('company', exp.company)
                exp.job_title = data.get('job_title', exp.job_title)
                exp.start_date = data.get('start_date', exp.start_date)
                exp.end_date = data.get('end_date') or None
                exp.is_current = data.get('is_current') == 'on'
                exp.description = data.get('description', '')
                exp.save()
            return 'updated'
        EmployeeExperience.objects.create(
            employee=emp,
            company=data.get('company'),
            job_title=data.get('job_title'),
            start_date=data.get('start_date'),
            end_date=data.get('end_date') or None,
            is_current=data.get('is_current') == 'on',
            description=data.get('description', ''),
        )
        return 'created'

    @staticmethod
    def add_skill(data):
        emp = SkillsService._resolve_employee(data.get('employee_id'))
        skill_name = data.get('skill_name')
        if not emp or not skill_name:
            return None
        existing = EmployeeSkill.objects.filter(employee=emp, skill_name=skill_name).first()
        if existing:
            existing.proficiency = data.get('proficiency', existing.proficiency)
            existing.years_of_experience = data.get('years_of_experience') or None
            existing.is_active = True
            existing.save()
        else:
            EmployeeSkill.objects.create(
                employee=emp,
                skill_name=skill_name,
                proficiency=data.get('proficiency', 'Intermediate'),
                years_of_experience=data.get('years_of_experience') or None,
            )
        return 'created'

    @staticmethod
    def add_competency_rating(data):
        emp = SkillsService._resolve_employee(data.get('employee_id'))
        comp_id = data.get('competency_id')
        if not emp or not comp_id:
            return None
        try:
            comp = Competency.objects.get(pk=comp_id)
        except (Competency.DoesNotExist, ValueError):
            comp = Competency.objects.filter(pk=comp_id).first()
        if not comp:
            return None
        existing = CompetencyRating.objects.filter(employee=emp, competency=comp).first()
        if existing:
            existing.rating = data.get('rating', existing.rating)
            existing.notes = data.get('notes', '')
            existing.save()
        else:
            CompetencyRating.objects.create(
                employee=emp,
                competency=comp,
                rating=data.get('rating'),
                notes=data.get('notes', ''),
            )
        return 'created'
