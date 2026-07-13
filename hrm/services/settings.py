from ..models import HRMSetting, LeavePolicy, RatingTemplate


class HRMSettingsService:
    @staticmethod
    def save_setting(key, value):
        setting, _ = HRMSetting.objects.get_or_create(key=key)
        setting.value = value
        setting.is_active = True
        setting.save(update_fields=['value', 'is_active'])

    @staticmethod
    def add_leave_policy(data):
        doc_id = data.get('doc_id')
        if doc_id:
            policy = LeavePolicy.objects.filter(pk=doc_id).first()
            if not policy:
                try:
                    policy = LeavePolicy.objects.get(pk=doc_id)
                except (LeavePolicy.DoesNotExist, ValueError):
                    pass
            if policy:
                policy.employee_type = data.get('employee_type', policy.employee_type)
                policy.leave_type = data.get('leave_type', policy.leave_type)
                policy.entitled_days = float(data.get('entitled_days', 0))
                policy.carry_forward_days = float(data.get('carry_forward_days', 0))
                policy.save()
            return 'updated'
        else:
            LeavePolicy.objects.get_or_create(
                employee_type=data.get('employee_type'),
                leave_type=data.get('leave_type'),
                defaults={
                    'entitled_days': float(data.get('entitled_days', 0)),
                    'carry_forward_days': float(data.get('carry_forward_days', 0)),
                },
            )
            return 'created'

    @staticmethod
    def add_rating_template(data):
        doc_id = data.get('doc_id')
        if doc_id:
            template = RatingTemplate.objects.filter(pk=doc_id).first()
            if not template:
                try:
                    template = RatingTemplate.objects.get(pk=doc_id)
                except (RatingTemplate.DoesNotExist, ValueError):
                    pass
            if template:
                template.name = data.get('name', template.name)
                template.description = data.get('description', '')
                template.save()
            return 'updated'
        else:
            RatingTemplate.objects.create(
                name=data.get('name'),
                description=data.get('description', ''),
            )
            return 'created'
