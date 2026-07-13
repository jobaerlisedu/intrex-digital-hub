from ..models import EngagementSurvey


class SurveyService:
    @staticmethod
    def add_survey(data):
        doc_id = data.get('doc_id')
        if doc_id:
            try:
                survey = EngagementSurvey.objects.get(pk=doc_id)
            except (EngagementSurvey.DoesNotExist, ValueError):
                survey = EngagementSurvey.objects.filter(pk=doc_id).first()
            if survey:
                survey.title = data.get('title', survey.title)
                survey.description = data.get('description', '')
                survey.start_date = data.get('start_date') or None
                survey.end_date = data.get('end_date') or None
                survey.is_anonymous = data.get('is_anonymous') == 'on'
                survey.status = data.get('status', survey.status)
                survey.save()
            return 'updated'
        else:
            survey = EngagementSurvey.objects.create(
                title=data.get('title'),
                description=data.get('description', ''),
                start_date=data.get('start_date') or None,
                end_date=data.get('end_date') or None,
                is_anonymous=data.get('is_anonymous') == 'on',
                status=data.get('status', 'Draft'),
            )
            return 'created'
