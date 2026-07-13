from ..models import ComplianceReminder, Employee


class ComplianceCalendarService:
    @staticmethod
    def add_reminder(data):
        emp_id = data.get('employee_id')
        if not emp_id:
            return None
        try:
            emp = Employee.objects.get(pk=emp_id)
        except (Employee.DoesNotExist, ValueError):
            emp = Employee.objects.filter(pk=emp_id).first()
        if not emp:
            return None

        doc_id = data.get('doc_id')
        if doc_id:
            reminder = ComplianceReminder.objects.filter(pk=doc_id).first()
            if reminder:
                reminder.employee = emp
                reminder.reminder_type = data.get('reminder_type', reminder.reminder_type)
                reminder.title = data.get('title', reminder.title)
                reminder.description = data.get('description', '')
                reminder.due_date = data.get('due_date', reminder.due_date)
                reminder.status = data.get('status', reminder.status)
                reminder.save()
            return 'updated'
        else:
            ComplianceReminder.objects.create(
                employee=emp,
                reminder_type=data.get('reminder_type'),
                title=data.get('title'),
                description=data.get('description', ''),
                due_date=data.get('due_date'),
                status=data.get('status', 'Pending'),
            )
            return 'created'
