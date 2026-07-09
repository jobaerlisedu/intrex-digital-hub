from config.firebase import db
from config.logger import hrm_logger
from ..audit import enrich_with_audit
from ..validators import validate_employee_data
from ..views_helpers import get_collection_data, get_cached_collection
from .base import FirestoreService


class EmployeeService(FirestoreService):
    collection_name = 'hrm_employees'

    @classmethod
    def save_employee(cls, data, user):
        doc_id = data.get('doc_id')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        full_name = f"{first_name} {last_name}".strip()
        email = data.get('email', '')
        phone = data.get('phone', '')

        from config.contacts_helper import get_or_create_contact
        contact_id = get_or_create_contact(name=full_name, email=email, phone=phone, role='employee')

        basic_salary = float(data.get('basic_salary') or 0)
        house_rent = round(basic_salary * 0.50, 2)
        medical = round(basic_salary * 0.20, 2)
        conveyance = round(basic_salary * 0.20, 2)
        utility = round(basic_salary * 0.10, 2)
        mobile_bill = float(data.get('mobile_bill') or 1000)
        gross_salary = round(basic_salary + house_rent + medical + conveyance + utility + mobile_bill, 2)

        additional_depts = data.getlist('additional_dept') if hasattr(data, 'getlist') else data.get('additional_dept', [])
        additional_subdepts = data.getlist('additional_subdept') if hasattr(data, 'getlist') else data.get('additional_subdept', [])
        additional_positions = data.getlist('additional_position') if hasattr(data, 'getlist') else data.get('additional_position', [])
        additional_roles = []
        for d, sd, p in zip(additional_depts, additional_subdepts, additional_positions):
            if d and p:
                additional_roles.append({'department': d, 'sub_department': sd or '', 'position': p})

        emp_data = {
            'name': full_name,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'phone': phone,
            'alt_phone': data.get('alt_phone', ''),
            'national_id': data.get('national_id', ''),
            'city': data.get('city', ''),
            'zip': data.get('zip', ''),
            'account_holder': data.get('account_holder', ''),
            'account_number': data.get('account_number', ''),
            'branch_name': data.get('branch_name', ''),
            'bank_name': data.get('bank_name', ''),
            'basic_salary': basic_salary,
            'house_rent': house_rent,
            'medical_allowance': medical,
            'conveyance_allowance': conveyance,
            'utility': utility,
            'mobile_bill': mobile_bill,
            'gross_salary': gross_salary,
            'department': data.get('department', ''),
            'sub_department': data.get('sub_department', ''),
            'position': data.get('position', ''),
            'additional_roles': additional_roles,
            'employee_type': data.get('employee_type', 'Permanent'),
            'joining_date': data.get('joining_date', ''),
            'status': data.get('employment_status', 'Active'),
            'exit_date': data.get('exit_date', ''),
            'exit_type': data.get('exit_type', ''),
            'exit_reason': data.get('exit_reason', ''),
            'dob': data.get('dob', ''),
            'gender': data.get('gender', ''),
            'marital_status': data.get('marital_status', ''),
            'religion': data.get('religion', ''),
            'ec_primary_name': data.get('ec_primary_name', ''),
            'ec_primary_relation': data.get('ec_primary_relation', ''),
            'ec_primary_mobile': data.get('ec_primary_mobile', ''),
            'ec_secondary_name': data.get('ec_secondary_name', ''),
            'ec_secondary_relation': data.get('ec_secondary_relation', ''),
            'ec_secondary_mobile': data.get('ec_secondary_mobile', ''),
            'contact_id': contact_id,
        }

        if doc_id:
            cls.update(doc_id, emp_data, user)
            emp_data['id'] = doc_id
            result = 'updated'
        else:
            existing = list(db.collection('hrm_employees').stream())
            count = len(existing) + 1
            emp_data['emp_id'] = f"EMP-{count:04d}"
            new_id = cls.create(emp_data, user)
            emp_data['id'] = new_id
            result = 'created'

        try:
            from config.services.integration_service import IntegrationService
            IntegrationService.employee_to_user_registry(emp_data)
        except Exception as e:
            hrm_logger.error(f"Error syncing employee to registry: {e}")

        return result

    @classmethod
    def get_all_employees(cls):
        try:
            docs = db.collection('hrm_employees').stream()
            employees = []
            for doc in docs:
                emp = doc.to_dict()
                emp['id'] = doc.id
                employees.append(emp)
            return employees
        except Exception as e:
            hrm_logger.error(f"Error fetching employees: {e}")
            return []

    @classmethod
    def get_employee_context(cls):
        employees = cls.get_all_employees()
        departments = get_cached_collection('org_departments')
        sub_departments = get_cached_collection('org_departments_sub')
        positions = get_cached_collection('org_positions')
        return employees, departments, sub_departments, positions
