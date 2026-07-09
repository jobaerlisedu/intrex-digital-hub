from .base import FirestoreService


class RosterService(FirestoreService):
    collection_name = 'hrm_employee_shifts'

    @classmethod
    def assign_shift(cls, data, user):
        cls.create({
            'employee': data.get('employee'),
            'shift_name': data.get('shift_name'),
            'start_date': data.get('start_date'),
            'end_date': data.get('end_date'),
        }, user)
