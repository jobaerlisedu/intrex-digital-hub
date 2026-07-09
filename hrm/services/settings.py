from ..models import HRMSetting, LeavePolicy, RatingTemplate, RatingScale


class HRMSettingsService:
    @staticmethod
    def save_setting(key, value):
        HRMSetting.objects.update_or_create(key=key, defaults={'value': value})

    @staticmethod
    def add_leave_policy(data):
        doc_id = data.get('doc_id')
        if doc_id:
            lp = LeavePolicy.objects.get(id=doc_id)
            lp.employee_type = data.get('employee_type')
            lp.leave_type = data.get('leave_type')
            lp.entitled_days = data.get('entitled_days')
            lp.carry_forward_days = data.get('carry_forward_days', 0)
            lp.save()
            return 'updated'
        else:
            LeavePolicy.objects.create(
                employee_type=data.get('employee_type'),
                leave_type=data.get('leave_type'),
                entitled_days=data.get('entitled_days'),
                carry_forward_days=data.get('carry_forward_days', 0),
            )
            return 'created'

    @staticmethod
    def add_rating_template(data):
        doc_id = data.get('doc_id')
        if doc_id:
            rt = RatingTemplate.objects.get(id=doc_id)
            rt.name = data.get('name')
            rt.description = data.get('description', '')
            rt.save()
            return 'updated'
        else:
            RatingTemplate.objects.create(
                name=data.get('name'),
                description=data.get('description', ''),
            )
            return 'created'
