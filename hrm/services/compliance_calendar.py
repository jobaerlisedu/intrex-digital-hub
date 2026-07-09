from ..models import ComplianceReminder


class ComplianceCalendarService:
    @staticmethod
    def add_reminder(data):
        emp_id = data.get('employee_id')
        if not emp_id:
            return None
        doc_id = data.get('doc_id')
        if doc_id:
            reminder = ComplianceReminder.objects.get(id=doc_id)
            reminder.reminder_type = data.get('reminder_type')
            reminder.title = data.get('title')
            reminder.description = data.get('description', '')
            reminder.due_date = data.get('due_date')
            reminder.status = data.get('status', 'Pending')
            reminder.save()
            return 'updated'
        else:
            ComplianceReminder.objects.create(
                employee_id=emp_id,
                reminder_type=data.get('reminder_type'),
                title=data.get('title'),
                description=data.get('description', ''),
                due_date=data.get('due_date'),
                status=data.get('status', 'Pending'),
            )
            return 'created'
