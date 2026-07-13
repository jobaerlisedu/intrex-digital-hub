from config.logger import hrm_logger
from .base import ORMService
from ..models import Employee, Department, Position


class EmployeeService(ORMService):
    model = Employee

    @classmethod
    def _resolve(cls, doc_id):
        if not doc_id:
            return None
        try:
            return cls.model.objects.get(pk=doc_id)
        except (cls.model.DoesNotExist, ValueError):
            pass
        return cls.model.objects.filter(pk=doc_id).first()

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
        house_rent = float(data.get('house_rent') or round(basic_salary * 0.50, 2))
        medical = float(data.get('medical_allowance') or round(basic_salary * 0.20, 2))
        conveyance = float(data.get('conveyance_allowance') or round(basic_salary * 0.20, 2))
        utility = float(data.get('utility') or round(basic_salary * 0.10, 2))
        mobile_bill = float(data.get('mobile_bill') or 1000)
        gross_salary = round(basic_salary + house_rent + medical + conveyance + utility + mobile_bill, 2)

        dept = None
        dept_id = data.get('department')
        if dept_id:
            try:
                dept = Department.objects.get(pk=dept_id)
            except (Department.DoesNotExist, ValueError):
                dept = Department.objects.filter(pk=dept_id).first()

        sub_dept = None
        sub_dept_id = data.get('sub_department')
        if sub_dept_id:
            try:
                sub_dept = Department.objects.get(pk=sub_dept_id)
            except (Department.DoesNotExist, ValueError):
                sub_dept = Department.objects.filter(pk=sub_dept_id).first()

        pos = None
        pos_id = data.get('position')
        if pos_id:
            try:
                pos = Position.objects.get(pk=pos_id)
            except (Position.DoesNotExist, ValueError):
                pos = Position.objects.filter(pk=pos_id).first()

        additional_depts = data.getlist('additional_dept') if hasattr(data, 'getlist') else data.get('additional_dept', [])
        additional_subdepts = data.getlist('additional_subdept') if hasattr(data, 'getlist') else data.get('additional_subdept', [])
        additional_positions = data.getlist('additional_position') if hasattr(data, 'getlist') else data.get('additional_position', [])

        if doc_id:
            instance = cls._resolve(doc_id)
            if instance:
                instance.first_name = first_name
                instance.last_name = last_name
                instance.email = email
                instance.phone = phone
                instance.alt_phone = data.get('alt_phone', '')
                instance.national_id = data.get('national_id', '')
                instance.city = data.get('city', '')
                instance.zip = data.get('zip', '')
                instance.account_holder = data.get('account_holder', '')
                instance.account_number = data.get('account_number', '')
                instance.branch_name = data.get('branch_name', '')
                instance.bank_name = data.get('bank_name', '')
                instance.basic_salary = basic_salary
                instance.house_rent = house_rent
                instance.medical_allowance = medical
                instance.conveyance_allowance = conveyance
                instance.utility = utility
                instance.mobile_bill = mobile_bill
                instance.gross_salary = gross_salary
                instance.department = dept
                instance.sub_department = sub_dept
                instance.position = pos
                instance.employee_type = data.get('employee_type', 'Permanent')
                instance.joining_date = data.get('joining_date') or None
                instance.status = data.get('employment_status', 'Active')
                instance.exit_date = data.get('exit_date') or None
                instance.exit_type = data.get('exit_type', '')
                instance.exit_reason = data.get('exit_reason', '')
                instance.dob = data.get('dob') or None
                instance.gender = data.get('gender', '')
                instance.marital_status = data.get('marital_status', '')
                instance.religion = data.get('religion', '')
                instance.ec_primary_name = data.get('ec_primary_name', '')
                instance.ec_primary_relation = data.get('ec_primary_relation', '')
                instance.ec_primary_mobile = data.get('ec_primary_mobile', '')
                instance.ec_secondary_name = data.get('ec_secondary_name', '')
                instance.ec_secondary_relation = data.get('ec_secondary_relation', '')
                instance.ec_secondary_mobile = data.get('ec_secondary_mobile', '')
                instance.contact_id = contact_id or instance.contact_id
                instance.updated_by = user
                instance.save()
                result = 'updated'
            else:
                result = 'created'
        else:
            count = Employee.objects.count() + 1
            emp_id = f"EMP-{count:04d}"
            instance = Employee.objects.create(
                emp_id=emp_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                alt_phone=data.get('alt_phone', ''),
                national_id=data.get('national_id', ''),
                city=data.get('city', ''),
                zip=data.get('zip', ''),
                account_holder=data.get('account_holder', ''),
                account_number=data.get('account_number', ''),
                branch_name=data.get('branch_name', ''),
                bank_name=data.get('bank_name', ''),
                basic_salary=basic_salary,
                house_rent=house_rent,
                medical_allowance=medical,
                conveyance_allowance=conveyance,
                utility=utility,
                mobile_bill=mobile_bill,
                gross_salary=gross_salary,
                department=dept,
                sub_department=sub_dept,
                position=pos,
                employee_type=data.get('employee_type', 'Permanent'),
                joining_date=data.get('joining_date') or None,
                status=data.get('employment_status', 'Active'),
                exit_date=data.get('exit_date') or None,
                exit_type=data.get('exit_type', ''),
                exit_reason=data.get('exit_reason', ''),
                dob=data.get('dob') or None,
                gender=data.get('gender', ''),
                marital_status=data.get('marital_status', ''),
                religion=data.get('religion', ''),
                ec_primary_name=data.get('ec_primary_name', ''),
                ec_primary_relation=data.get('ec_primary_relation', ''),
                ec_primary_mobile=data.get('ec_primary_mobile', ''),
                ec_secondary_name=data.get('ec_secondary_name', ''),
                ec_secondary_relation=data.get('ec_secondary_relation', ''),
                ec_secondary_mobile=data.get('ec_secondary_mobile', ''),
                contact_id=contact_id or '',
                created_by=user,
                updated_by=user,
            )
            result = 'created'

        try:
            from config.services.integration_service import IntegrationService
            emp_data = {
                'id': str(instance.pk),
                'first_name': first_name,
                'last_name': last_name,
                'name': instance.name,
                'email': email,
                'phone': phone,
                'contact_id': contact_id,
                'department': data.get('department', ''),
                'position': data.get('position', ''),
                'employee_type': data.get('employee_type', 'Permanent'),
                'status': data.get('employment_status', 'Active'),
            }
            IntegrationService.employee_to_user_registry(emp_data)
        except Exception as e:
            hrm_logger.error(f"Error syncing employee to registry: {e}")

        return result

    @classmethod
    def get_all_employees(cls):
        try:
            return list(Employee.objects.filter(is_active=True).order_by('emp_id'))
        except Exception as e:
            hrm_logger.error(f"Error fetching employees: {e}")
            return []

    @classmethod
    def get_employee_context(cls):
        employees = cls.get_all_employees()
        departments = list(Department.objects.filter(is_active=True, parent__isnull=True).values('id', 'name'))
        sub_departments = list(Department.objects.filter(is_active=True, parent__isnull=False).values('id', 'name', 'parent__name'))
        positions = list(Position.objects.filter(is_active=True).values('id', 'title', 'department__name', 'sub_department__name'))
        return employees, departments, sub_departments, positions
