from datetime import date, datetime


def _is_valid_date(value):
    if not value:
        return False
    try:
        date.fromisoformat(str(value))
        return True
    except (ValueError, TypeError):
        return False


def _is_valid_float(value):
    if value is None or value == '':
        return False
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def validate_employee_data(data):
    errors = []
    if not data.get('first_name', '').strip():
        errors.append('First name is required')
    if not data.get('last_name', '').strip():
        errors.append('Last name is required')
    if not data.get('email', '').strip():
        errors.append('Email is required')
    if data.get('joining_date') and not _is_valid_date(data.get('joining_date')):
        errors.append('Invalid joining date format (use YYYY-MM-DD)')
    if data.get('dob') and not _is_valid_date(data.get('dob')):
        errors.append('Invalid date of birth format (use YYYY-MM-DD)')
    if data.get('exit_date') and not _is_valid_date(data.get('exit_date')):
        errors.append('Invalid exit date format (use YYYY-MM-DD)')
    basic = data.get('basic_salary')
    if basic is not None and not _is_valid_float(basic):
        errors.append('Basic salary must be a number')
    if data.get('status') and data['status'] not in ('Active', 'Inactive', 'On Leave', 'Resigned', 'Terminated'):
        errors.append('Invalid employment status')
    return errors


def validate_attendance_data(data):
    errors = []
    if not data.get('name', '').strip():
        errors.append('Employee name is required')
    if not data.get('date', '').strip():
        errors.append('Date is required')
    elif not _is_valid_date(data.get('date')):
        errors.append('Invalid date format (use YYYY-MM-DD)')
    if data.get('status') and data['status'] not in ('Present', 'Absent', 'Late', 'Half Day', 'On Leave'):
        errors.append('Invalid attendance status')
    return errors


def validate_leave_data(data):
    errors = []
    if not data.get('emp_name', '').strip() and not data.get('name', '').strip():
        errors.append('Employee name is required')
    if not data.get('leave_type', '').strip() and not data.get('type', '').strip():
        errors.append('Leave type is required')
    from_date = data.get('from_date', '')
    to_date = data.get('to_date', '')
    if not from_date:
        errors.append('Start date is required')
    elif not _is_valid_date(from_date):
        errors.append('Invalid start date format (use YYYY-MM-DD)')
    if not to_date:
        errors.append('End date is required')
    elif not _is_valid_date(to_date):
        errors.append('Invalid end date format (use YYYY-MM-DD)')
    if from_date and to_date and _is_valid_date(from_date) and _is_valid_date(to_date):
        fd = date.fromisoformat(str(from_date))
        td = date.fromisoformat(str(to_date))
        if td < fd:
            errors.append('End date cannot be before start date')
    return errors


def validate_candidate_data(data):
    errors = []
    if not data.get('name', '').strip():
        errors.append('Candidate name is required')
    if not data.get('position', '').strip():
        errors.append('Position is required')
    return errors


def validate_department_data(data):
    errors = []
    if not data.get('name', '').strip():
        errors.append('Department name is required')
    return errors


def validate_position_data(data):
    errors = []
    if not data.get('title', '').strip():
        errors.append('Position title is required')
    if not data.get('dept_id', '').strip():
        errors.append('Department is required')
    return errors


def validate_advance_data(data):
    errors = []
    if not data.get('employee', '').strip():
        errors.append('Employee name is required')
    amount = data.get('amount', 0)
    if not _is_valid_float(amount):
        errors.append('Amount must be a number')
    elif float(amount) <= 0:
        errors.append('Amount must be greater than zero')
    if not data.get('deduct_month', '').strip():
        errors.append('Deduction month is required')
    return errors


def validate_expense_data(data):
    errors = []
    if not data.get('employee', '').strip():
        errors.append('Employee name is required')
    if not data.get('category', '').strip():
        errors.append('Category is required')
    if not _is_valid_float(data.get('amount', 0)):
        errors.append('Amount must be a number')
    elif float(data.get('amount', 0)) <= 0:
        errors.append('Amount must be greater than zero')
    return errors


def validate_shift_data(data):
    errors = []
    if not data.get('employee', '').strip():
        errors.append('Employee name is required')
    if not data.get('shift_name', '').strip():
        errors.append('Shift name is required')
    if data.get('start_date') and not _is_valid_date(data.get('start_date')):
        errors.append('Invalid start date format (use YYYY-MM-DD)')
    if data.get('end_date') and not _is_valid_date(data.get('end_date')):
        errors.append('Invalid end date format (use YYYY-MM-DD)')
    return errors


def validate_document_data(data):
    errors = []
    if not data.get('employee', '').strip():
        errors.append('Employee name is required')
    if not data.get('document_type', '').strip():
        errors.append('Document type is required')
    if data.get('expiry_date') and not _is_valid_date(data.get('expiry_date')):
        errors.append('Invalid expiry date format (use YYYY-MM-DD)')
    return errors


def validate_asset_data(data):
    errors = []
    if not data.get('employee', '').strip():
        errors.append('Employee name is required')
    if not data.get('asset_name', '').strip():
        errors.append('Asset name is required')
    return errors


def validate_payroll_data(data):
    errors = []
    if not data.get('month', '').strip():
        errors.append('Month is required')
    if not data.get('year', '').strip():
        errors.append('Year is required')
    return errors


def validate_holiday_data(data):
    errors = []
    if not data.get('holiday_name', '').strip():
        errors.append('Holiday name is required')
    from_date = data.get('from_date', '')
    to_date = data.get('to_date', '')
    if not from_date:
        errors.append('Start date is required')
    if not to_date:
        errors.append('End date is required')
    return errors


def validate_disciplinary_data(data):
    errors = []
    if not data.get('employee', '').strip():
        errors.append('Employee is required')
    if not data.get('incident_date', '').strip():
        errors.append('Incident date is required')
    elif not _is_valid_date(data.get('incident_date')):
        errors.append('Invalid incident date format (use YYYY-MM-DD)')
    if not data.get('nature_of_offense', '').strip():
        errors.append('Nature of offense is required')
    if data.get('severity') and data['severity'] not in ('Minor', 'Major', 'Gross'):
        errors.append('Invalid severity level')
    return errors


def validate_hearing_data(data):
    errors = []
    if not data.get('case_id', '').strip():
        errors.append('Case is required')
    if not data.get('hearing_date', '').strip():
        errors.append('Hearing date is required')
    return errors


def validate_action_data(data):
    errors = []
    if not data.get('case_id', '').strip():
        errors.append('Case is required')
    if not data.get('action_type', '').strip():
        errors.append('Action type is required')
    if not data.get('issued_date', '').strip():
        errors.append('Issued date is required')
    if not data.get('effective_date', '').strip():
        errors.append('Effective date is required')
    return errors


def validate_appeal_data(data):
    errors = []
    if not data.get('action_id', '').strip():
        errors.append('Action is required')
    if not data.get('appeal_date', '').strip():
        errors.append('Appeal date is required')
    if not data.get('grounds', '').strip():
        errors.append('Grounds for appeal are required')
    return errors
