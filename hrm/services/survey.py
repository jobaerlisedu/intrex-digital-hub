from ..models import EngagementSurvey, SurveyQuestion, SurveyResponse


class SurveyService:
    @staticmethod
    def add_survey(data):
        doc_id = data.get('doc_id')
        if doc_id:
            survey = EngagementSurvey.objects.get(id=doc_id)
            survey.title = data.get('title')
            survey.description = data.get('description', '')
            survey.start_date = data.get('start_date')
            survey.end_date = data.get('end_date')
            survey.is_anonymous = data.get('is_anonymous') == 'on'
            survey.status = data.get('status', 'Draft')
            survey.save()
            return 'updated'
        else:
            EngagementSurvey.objects.create(
                title=data.get('title'),
                description=data.get('description', ''),
                start_date=data.get('start_date'),
                end_date=data.get('end_date'),
                is_anonymous=data.get('is_anonymous') == 'on',
                status=data.get('status', 'Draft'),
            )
            return 'created'
