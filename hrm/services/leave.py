from datetime import date as dt
from .base import ORMService
from ..models import Leave, Holiday, Employee, LeaveBalance, LeavePolicy, HRMSetting
from config.workflow_integration import ensure_workflow, try_transition, LEAVE_TRIGGER_MAP


class LeaveService(ORMService):
    model = Leave

    @classmethod
    def _resolve(cls, doc_id, model_class=None):
        if not doc_id:
            return None
        mc = model_class or cls.model
        try:
            return mc.objects.get(pk=doc_id)
        except (mc.DoesNotExist, ValueError):
            pass
        return mc.objects.filter(pk=doc_id).first()

    @classmethod
    def add_holiday(cls, data, user):
        doc_id = data.get('doc_id')
        if doc_id:
            instance = cls._resolve(doc_id, Holiday)
            if instance:
                instance.holiday_name = data.get('holiday_name', instance.holiday_name)
                instance.from_date = data.get('from_date', instance.from_date)
                instance.to_date = data.get('to_date', instance.to_date)
                instance.holiday_type = data.get('holiday_type', instance.holiday_type)
                instance.save()
            return 'updated'
        else:
            Holiday.objects.create(
                holiday_name=data.get('holiday_name'),
                from_date=data.get('from_date'),
                to_date=data.get('to_date'),
                holiday_type=data.get('holiday_type', 'Public'),
            )
            return 'created'

    @classmethod
    def delete_holiday(cls, doc_id):
        instance = cls._resolve(doc_id, Holiday)
        if instance:
            instance.is_active = False
            instance.save(update_fields=['is_active'])

    @classmethod
    def apply_leave(cls, data, user):
        doc_id = data.get('doc_id')
        from_date_str = data.get('from_date', '')
        to_date_str = data.get('to_date', '')
        try:
            fd = dt.fromisoformat(from_date_str)
            td = dt.fromisoformat(to_date_str)
            days = (td - fd).days + 1
            duration = f"{days} Day{'s' if days != 1 else ''}"
        except Exception:
            duration = data.get('duration', '')

        emp_name = data.get('emp_name')
        emp = Employee.objects.filter(name=emp_name).first()

        if doc_id:
            instance = cls._resolve(doc_id)
            if instance:
                instance.employee = emp or instance.employee
                instance.leave_type = data.get('leave_type', instance.leave_type)
                instance.from_date = from_date_str or instance.from_date
                instance.to_date = to_date_str or instance.to_date
                instance.duration = duration
                instance.reason = data.get('reason', '')
                instance.save()
                ensure_workflow('hrm', 'leave', str(instance.pk), entity_label=emp_name or '')
            return 'updated'
        else:
            instance = Leave.objects.create(
                employee=emp,
                leave_type=data.get('leave_type'),
                from_date=from_date_str,
                to_date=to_date_str,
                duration=duration,
                reason=data.get('reason', ''),
                status='Pending',
                created_by=user,
                updated_by=user,
            )
            ensure_workflow('hrm', 'leave', str(instance.pk), entity_label=emp_name or '')
            return 'created'

    @classmethod
    def approve_or_reject(cls, doc_id, status, user):
        instance = cls._resolve(doc_id)
        if instance:
            instance.status = status
            instance.updated_by = user
            instance.save(update_fields=['status', 'updated_by'])
            ensure_workflow('hrm', 'leave', str(instance.pk))
            trigger = LEAVE_TRIGGER_MAP.get(status)
            if trigger:
                try_transition('hrm', 'leave', str(instance.pk), trigger)

    @classmethod
    def save_weekend(cls, weekend_days):
        setting, _ = HRMSetting.objects.get_or_create(key='weekend')
        setting.value = {'days': weekend_days}
        setting.save(update_fields=['value'])

    @classmethod
    def delete(cls, doc_id):
        instance = cls._resolve(doc_id)
        if instance:
            instance.is_active = False
            instance.save(update_fields=['is_active'])

    @classmethod
    def get_leave_context(cls):
        holidays = list(Holiday.objects.filter(is_active=True).values(
            'pk', 'holiday_name', 'from_date', 'to_date', 'holiday_type',
        ))
        for h in holidays:
            h['id'] = h.pop('pk') or ''
            h['type'] = h.pop('holiday_type', '')
            h['from_date'] = str(h['from_date']) if h['from_date'] else ''
            h['to_date'] = str(h['to_date']) if h['to_date'] else ''

        leaves = list(Leave.objects.filter(is_active=True).select_related('employee').order_by('-from_date').values(
            'pk', 'employee__name', 'leave_type', 'from_date', 'to_date', 'duration', 'reason', 'status',
        ))
        for l in leaves:
            l['id'] = l.pop('pk') or ''
            l['name'] = l.pop('employee__name', '')
            l['type'] = l.pop('leave_type', '')
            l['from_date'] = str(l['from_date']) if l['from_date'] else ''
            l['to_date'] = str(l['to_date']) if l['to_date'] else ''

        try:
            employees = [{'name': e.name, 'id': str(e.pk)} for e in Employee.objects.filter(is_active=True) if e.name]
        except Exception:
            employees = []

        try:
            ws = HRMSetting.objects.filter(key='weekend').first()
            weekend_days = ws.value.get('days', ['Saturday', 'Sunday']) if ws else ['Saturday', 'Sunday']
        except Exception:
            weekend_days = ['Saturday', 'Sunday']

        try:
            emp_balances = []
            for emp in Employee.objects.filter(is_active=True):
                balances = LeaveBalance.objects.filter(employee=emp, is_active=True)
                emp_balances.append({
                    'name': emp.name,
                    'balances': [
                        {
                            'leave_type': b.leave_type,
                            'entitled': float(b.entitled),
                            'used': float(b.used),
                            'pending': float(b.pending),
                            'available': float(b.available),
                        }
                        for b in balances
                    ],
                })
        except Exception:
            emp_balances = []

        return holidays, leaves, employees, weekend_days, emp_balances
