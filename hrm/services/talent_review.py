from ..models import TalentReviewMeeting, NineBoxCell


class TalentReviewService:
    @staticmethod
    def add_meeting(data):
        doc_id = data.get('doc_id')
        if doc_id:
            meeting = TalentReviewMeeting.objects.get(id=doc_id)
            meeting.title = data.get('title')
            meeting.meeting_date = data.get('meeting_date')
            meeting.notes = data.get('notes', '')
            meeting.status = data.get('status', 'Scheduled')
            meeting.save()
            return 'updated'
        else:
            TalentReviewMeeting.objects.create(
                title=data.get('title'),
                meeting_date=data.get('meeting_date'),
                notes=data.get('notes', ''),
                status=data.get('status', 'Scheduled'),
            )
            return 'created'

    @staticmethod
    def set_nine_box(data):
        meeting_id = data.get('meeting_id')
        emp_id = data.get('employee_id')
        if not meeting_id or not emp_id:
            return None
        NineBoxCell.objects.update_or_create(
            talent_review_id=meeting_id, employee_id=emp_id,
            defaults={
                'performance': data.get('performance'),
                'potential': data.get('potential'),
                'notes': data.get('notes', ''),
            }
        )
        return 'saved'
