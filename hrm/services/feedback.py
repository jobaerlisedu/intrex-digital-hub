from ..models import FeedbackQuestion, FeedbackRequest, FeedbackResponse


class FeedbackService:
    @staticmethod
    def add_question(data):
        FeedbackQuestion.objects.create(
            category=data.get('category'),
            question_text=data.get('question_text'),
            is_required=data.get('is_required') == 'on',
            order=data.get('order', 0),
        )
        return 'created'

    @staticmethod
    def add_request(data):
        reviewer_id = data.get('reviewer_id')
        reviewee_id = data.get('reviewee_id')
        cycle_id = data.get('review_cycle_id')
        if not all([reviewer_id, reviewee_id]):
            return None
        FeedbackRequest.objects.update_or_create(
            reviewer_id=reviewer_id, reviewee_id=reviewee_id, review_cycle_id=cycle_id,
            defaults={
                'relationship': data.get('relationship', ''),
                'status': 'Pending',
                'due_date': data.get('due_date'),
            }
        )
        return 'created'
