from ..models import EmployeeEducation, EmployeeExperience, EmployeeSkill, Competency, CompetencyRating


class SkillsService:
    @staticmethod
    def add_education(data):
        emp_id = data.get('employee_id')
        if not emp_id:
            return None
        doc_id = data.get('doc_id')
        if doc_id:
            edu = EmployeeEducation.objects.get(id=doc_id)
            edu.degree = data.get('degree')
            edu.institution = data.get('institution')
            edu.field_of_study = data.get('field_of_study')
            edu.start_year = data.get('start_year')
            edu.end_year = data.get('end_year')
            edu.grade = data.get('grade')
            edu.save()
            return 'updated'
        else:
            EmployeeEducation.objects.create(
                employee_id=emp_id, degree=data.get('degree'),
                institution=data.get('institution'), field_of_study=data.get('field_of_study'),
                start_year=data.get('start_year'), end_year=data.get('end_year'),
                grade=data.get('grade'),
            )
            return 'created'

    @staticmethod
    def add_experience(data):
        emp_id = data.get('employee_id')
        if not emp_id:
            return None
        doc_id = data.get('doc_id')
        if doc_id:
            exp = EmployeeExperience.objects.get(id=doc_id)
            exp.company = data.get('company')
            exp.job_title = data.get('job_title')
            exp.start_date = data.get('start_date')
            exp.end_date = data.get('end_date')
            exp.is_current = data.get('is_current') == 'on'
            exp.description = data.get('description', '')
            exp.save()
            return 'updated'
        else:
            EmployeeExperience.objects.create(
                employee_id=emp_id, company=data.get('company'),
                job_title=data.get('job_title'), start_date=data.get('start_date'),
                end_date=data.get('end_date'),
                is_current=data.get('is_current') == 'on',
                description=data.get('description', ''),
            )
            return 'created'

    @staticmethod
    def add_skill(data):
        emp_id = data.get('employee_id')
        if not emp_id:
            return None
        skill_name = data.get('skill_name')
        if not skill_name:
            return None
        EmployeeSkill.objects.update_or_create(
            employee_id=emp_id, skill_name=skill_name,
            defaults={
                'proficiency': data.get('proficiency'),
                'years_of_experience': data.get('years_of_experience'),
            }
        )
        return 'created'

    @staticmethod
    def add_competency_rating(data):
        emp_id = data.get('employee_id')
        comp_id = data.get('competency_id')
        if not emp_id or not comp_id:
            return None
        CompetencyRating.objects.update_or_create(
            employee_id=emp_id, competency_id=comp_id,
            defaults={
                'rating': data.get('rating'),
                'assessed_by': data.get('assessed_by'),
            }
        )
        return 'created'
