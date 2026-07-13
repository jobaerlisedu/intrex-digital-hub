from ..models import TalentReviewMeeting, NineBoxCell, Employee


class TalentReviewService:
    @staticmethod
    def _resolve_talent_meeting(meeting_id):
        if not meeting_id:
            return None
        try:
            return TalentReviewMeeting.objects.get(pk=meeting_id)
        except (TalentReviewMeeting.DoesNotExist, ValueError):
            pass
        return TalentReviewMeeting.objects.filter(pk=meeting_id).first()

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
    def add_meeting(data):
        doc_id = data.get('doc_id')
        if doc_id:
            meeting = TalentReviewService._resolve_talent_meeting(doc_id)
            if meeting:
                meeting.title = data.get('title', meeting.title)
                meeting.meeting_date = data.get('meeting_date', meeting.meeting_date)
                meeting.notes = data.get('notes', '')
                meeting.status = data.get('status', meeting.status)
                meeting.save()
            return 'updated'
        else:
            meeting = TalentReviewMeeting.objects.create(
                title=data.get('title'),
                meeting_date=data.get('meeting_date'),
                notes=data.get('notes', ''),
                status=data.get('status', 'Draft'),
            )
            return 'created'

    @staticmethod
    def set_nine_box(data):
        meeting = TalentReviewService._resolve_talent_meeting(data.get('meeting_id'))
        emp = TalentReviewService._resolve_employee(data.get('employee_id'))
        if not meeting or not emp:
            return None

        existing = NineBoxCell.objects.filter(talent_review=meeting, employee=emp).first()
        if existing:
            existing.performance = data.get('performance', existing.performance)
            existing.potential = data.get('potential', existing.potential)
            existing.notes = data.get('notes', '')
            existing.save()
        else:
            NineBoxCell.objects.create(
                talent_review=meeting,
                employee=emp,
                performance=data.get('performance'),
                potential=data.get('potential'),
                notes=data.get('notes', ''),
            )
        return 'saved'
