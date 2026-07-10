from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps


class Command(BaseCommand):
    help = 'Create database tables for models that had managed=False in older migrations'

    def handle(self, *args, **options):
        from hrm.models import (
            CandidateDocument, PayrollEmployee, HRMSetting,
            EmployeeEducation, EmployeeExperience, EmployeeSkill,
            Competency, CompetencyRating,
            FeedbackQuestion, FeedbackRequest, FeedbackResponse,
            EngagementSurvey, SurveyQuestion, SurveyResponse,
            ComplianceReminder, TalentReviewMeeting, NineBoxCell,
            DisciplinaryCase, DisciplinaryHearing, DisciplinaryAction, DisciplinaryAppeal,
            NotificationPreference, DeviceToken,
        )

        models = [
            CandidateDocument, PayrollEmployee, HRMSetting,
            EmployeeEducation, EmployeeExperience, EmployeeSkill,
            Competency, CompetencyRating,
            FeedbackQuestion, FeedbackRequest, FeedbackResponse,
            EngagementSurvey, SurveyQuestion, SurveyResponse,
            ComplianceReminder, TalentReviewMeeting, NineBoxCell,
            DisciplinaryCase, DisciplinaryHearing, DisciplinaryAction, DisciplinaryAppeal,
            NotificationPreference, DeviceToken,
        ]

        with connection.schema_editor() as schema_editor:
            for model in models:
                table_name = model._meta.db_table
                if not connection.introspection.table_names():
                    pass  # will be caught below
                if table_name not in connection.introspection.table_names():
                    self.stdout.write(f"Creating table: {table_name}")
                    schema_editor.create_model(model)
                else:
                    self.stdout.write(f"Table exists: {table_name}")
