from ..models import FeedbackQuestion, FeedbackRequest, Employee, ReviewCycle


class FeedbackService:
    @staticmethod
    def add_question(data):
        FeedbackQuestion.objects.create(
            category=data.get('category', 'General'),
            question_text=data.get('question_text'),
            is_required=data.get('is_required') == 'on',
            order=int(data.get('order', 0)),
        )
        return 'created'

    @staticmethod
    def add_request(data):
        reviewer_id = data.get('reviewer_id')
        reviewee_id = data.get('reviewee_id')
        if not reviewer_id or not reviewee_id:
            return None

        reviewee = Employee.objects.filter(pk=reviewee_id).first()
        if not reviewee:
            try:
                reviewee = Employee.objects.get(pk=reviewee_id)
            except (Employee.DoesNotExist, ValueError):
                return None

        cycle = None
        cycle_id = data.get('review_cycle_id')
        if cycle_id:
            try:
                cycle = ReviewCycle.objects.get(pk=cycle_id)
            except (ReviewCycle.DoesNotExist, ValueError):
                cycle = ReviewCycle.objects.filter(pk=cycle_id).first()

        existing = FeedbackRequest.objects.filter(
            reviewer_id=reviewer_id, reviewee=reviewee, review_cycle=cycle
        ).first()

        if existing:
            existing.relationship = data.get('relationship', '')
            existing.status = data.get('status', 'Pending')
            existing.due_date = data.get('due_date') or None
            existing.save()
        else:
            FeedbackRequest.objects.create(
                reviewer_id=reviewer_id,
                reviewee=reviewee,
                review_cycle=cycle,
                relationship=data.get('relationship', ''),
                status=data.get('status', 'Pending'),
                due_date=data.get('due_date') or None,
            )
        return 'created'
