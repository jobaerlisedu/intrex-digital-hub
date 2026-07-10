from decimal import Decimal
from datetime import datetime, timedelta, date
from config.firebase import db
from config.logger import hrm_logger


def calculate_payroll(period, employee_ids, user, tax_rate=Decimal('0.05')):
    year_month = period
    now = datetime.now().isoformat()
    emp_docs = list(db.collection('hrm_employees').stream())
    employees = []
    for d in emp_docs:
        data = d.to_dict()
        if data.get('id') in employee_ids or d.id in employee_ids:
            if data.get('status') == 'Active':
                employees.append({**data, 'id': d.id})

    payroll_ref = db.collection('hrm_payrolls').document()
    payroll_data = {
        'period': period,
        'employee_count': len(employees),
        'status': 'Draft',
        'created_by': f'users/{user.id}',
        'created_at': now,
        'updated_at': now,
        'is_active': True,
    }
    payroll_ref.set(payroll_data)
    total_net = Decimal('0.00')

    for emp in employees:
        basic = Decimal(str(emp.get('basic_salary', '0')))
        house_rent = Decimal(str(emp.get('house_rent', '0')))
        medical = Decimal(str(emp.get('medical_allowance', '0')))
        conveyance = Decimal(str(emp.get('conveyance_allowance', '0')))
        utility = Decimal(str(emp.get('utility', '0')))
        mobile = Decimal(str(emp.get('mobile_bill', '0')))
        gross = basic + house_rent + medical + conveyance + utility + mobile

        tax_deduction = (basic * tax_rate).quantize(Decimal('0.01'))
        advance_total = Decimal('0.00')
        try:
            advances = list(db.collection('hrm_advances')
                           .where('employee', '==', f'hrm_employees/{emp["id"]}')
                           .where('deduct_month', '==', year_month)
                           .where('status', '==', 'Pending')
                           .where('is_active', '==', True)
                           .stream())
            advance_total = sum(Decimal(str(a.to_dict().get('amount', '0'))) for a in advances)
        except Exception:
            pass

        absent_count = 0
        try:
            absent_docs = list(db.collection('hrm_attendances')
                             .where('employee', '==', f'hrm_employees/{emp["id"]}')
                             .where('status', '==', 'Absent')
                             .stream())
            absent_count = sum(1 for a in absent_docs if a.to_dict().get('date', '').startswith(year_month))
        except Exception:
            pass

        daily_rate = basic / Decimal('30') if basic else Decimal('0')
        absent_deduction = (daily_rate * Decimal(str(absent_count))).quantize(Decimal('0.01'))
        total_deductions = tax_deduction + advance_total + absent_deduction
        net = (gross - total_deductions).quantize(Decimal('0.01'))
        if net < 0:
            net = Decimal('0.00')

        db.collection('hrm_payroll_employees').add({
            'payroll': f'hrm_payrolls/{payroll_ref.id}',
            'employee': f'hrm_employees/{emp["id"]}',
            'basic_salary': str(basic),
            'house_rent': str(house_rent),
            'medical_allowance': str(medical),
            'conveyance_allowance': str(conveyance),
            'utility': str(utility),
            'mobile_bill': str(mobile),
            'gross_pay': str(gross),
            'deductions': str(total_deductions),
            'net_pay': str(net),
            'created_at': now,
            'updated_at': now,
            'is_active': True,
        })
        total_net += net
        try:
            for a in advances:
                db.collection('hrm_advances').document(a.id).update({'status': 'Deducted'})
        except Exception:
            pass

    payroll_ref.update({
        'total_net_pay': str(total_net.quantize(Decimal('0.01'))),
    })
    return payroll_ref.id


def get_employee_leave_balance(employee_ref, leave_type='Annual'):
    employee_id = employee_ref.split('/')[-1] if '/' in str(employee_ref) else str(employee_ref)
    emp_doc = db.collection('hrm_employees').document(employee_id).get()
    if not emp_doc.exists:
        return 0.0
    emp_data = emp_doc.to_dict() or {}
    employee_type = emp_data.get('employee_type', '')
    now_date = date.today()
    period = now_date.strftime('%Y')

    policy_docs = list(db.collection('hrm_leave_policies')
                      .where('employee_type', '==', employee_type)
                      .where('leave_type', '==', leave_type)
                      .where('is_active', '==', True)
                      .limit(1).stream())
    entitled = 20
    if policy_docs:
        entitled = int(policy_docs[0].to_dict().get('entitled_days', 20))

    balance_docs = list(db.collection('hrm_leave_balances')
                       .where('employee', '==', f'hrm_employees/{employee_id}')
                       .where('leave_type', '==', leave_type)
                       .where('period', '==', period)
                       .limit(1).stream())
    if balance_docs:
        b = balance_docs[0].to_dict()
        used = float(b.get('used', 0))
        pending = float(b.get('pending', 0))
    else:
        now = datetime.now().isoformat()
        db.collection('hrm_leave_balances').add({
            'employee': f'hrm_employees/{employee_id}',
            'leave_type': leave_type,
            'period': period,
            'entitled': entitled,
            'used': 0,
            'pending': 0,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        })
        used = 0
        pending = 0

    return max(0, float(entitled - used - pending))


def sync_document_compliance_reminders():
    synced = 0
    try:
        doc_docs = list(db.collection('hrm_documents')
                       .where('is_active', '==', True)
                       .stream())
        today = date.today()
        for d in doc_docs:
            data = d.to_dict()
            expiry = data.get('expiry_date')
            if not expiry:
                continue
            try:
                expiry_date = date.fromisoformat(expiry) if isinstance(expiry, str) else expiry
            except Exception:
                continue
            due_date = expiry_date - timedelta(days=30)
            employee_ref = data.get('employee', '')
            reminder_data = {
                'employee': employee_ref,
                'title': f"Document expiry: {data.get('document_type', 'Document')}",
                'reminder_type': 'Document Expiry',
                'due_date': due_date.isoformat(),
                'status': 'Overdue' if due_date < today else 'Pending',
                'document_ref': f'hrm_documents/{d.id}',
                'is_active': True,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }
            db.collection('hrm_compliance_reminders').add(reminder_data)
            synced += 1
    except Exception as e:
        hrm_logger.error(f"Error syncing compliance reminders: {e}")
    return {'synced': synced}


def check_compliance_overdue_reminders():
    try:
        today = date.today()
        reminders = list(db.collection('hrm_compliance_reminders')
                        .where('is_active', '==', True)
                        .stream())
        count = 0
        for r in reminders:
            data = r.to_dict()
            due = data.get('due_date')
            status = data.get('status', '')
            if due and status != 'Completed':
                try:
                    due_date = date.fromisoformat(due) if isinstance(due, str) else due
                    if due_date < today:
                        db.collection('hrm_compliance_reminders').document(r.id).update({
                            'status': 'Overdue',
                            'updated_at': datetime.now().isoformat(),
                        })
                        count += 1
                except Exception:
                    pass
        return {'marked_overdue': count}
    except Exception as e:
        hrm_logger.error(f"Error checking overdue reminders: {e}")
        return {'marked_overdue': 0}


def send_compliance_notifications():
    from config.services.notification_service import NotificationService
    try:
        today = date.today()
        reminders = list(db.collection('hrm_compliance_reminders')
                        .where('is_active', '==', True)
                        .stream())
        sent = 0
        for r in reminders:
            data = r.to_dict()
            due = data.get('due_date')
            if not due:
                continue
            try:
                due_date = date.fromisoformat(due) if isinstance(due, str) else due
            except Exception:
                continue
            employee_ref = data.get('employee', '')
            employee_id = employee_ref.split('/')[-1] if '/' in employee_ref else ''
            emp_doc = db.collection('hrm_employees').document(employee_id).get() if employee_id else None
            email = emp_doc.to_dict().get('email', '') if emp_doc and emp_doc.exists else ''
            if not email:
                continue
            status = data.get('status', '')
            title = data.get('title', 'Compliance Reminder')
            if status == 'Overdue':
                NotificationService.send_notification(
                    recipient=email,
                    title='Compliance Reminder Overdue',
                    message=f"'{title}' was due on {due}. Please complete immediately.",
                    channel='email',
                )
                sent += 1
            elif status == 'Pending' and today <= due_date <= today + timedelta(days=7):
                NotificationService.send_notification(
                    recipient=email,
                    title='Upcoming Compliance Deadline',
                    message=f"'{title}' is due on {due}.",
                    channel='email',
                )
                sent += 1
        return {'notifications_sent': sent}
    except Exception as e:
        hrm_logger.error(f"Error sending compliance notifications: {e}")
        return {'notifications_sent': 0}
