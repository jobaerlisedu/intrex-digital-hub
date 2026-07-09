from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from config.firebase import db
from django.contrib.auth.decorators import login_required
from accounts.decorators import module_access
from config.workflow_integration import ensure_workflow, try_transition, LEAVE_TRIGGER_MAP
from config.logger import hrm_logger
from .views_helpers import get_collection_data, get_cached_collection, invalidate_cache
from .validators import (
    validate_employee_data, validate_attendance_data, validate_leave_data,
    validate_candidate_data, validate_department_data, validate_position_data,
    validate_advance_data, validate_expense_data, validate_shift_data,
    validate_document_data, validate_asset_data, validate_holiday_data,
)
from .audit import enrich_with_audit
from django.utils import timezone
from .services import (
    RecruitmentService, DepartmentService, EmployeeService,
    AttendanceService, LeaveService, PayrollService, RosterService,
    ExpenseService, DocumentAssetService, OnboardingService,
    PerformanceService, DisciplineService,
)
from .services.notification import NotificationService as NotifService
from .services.succession import SuccessionService
from .services.skills import SkillsService
from .services.feedback import FeedbackService
from .services.survey import SurveyService
from .services.compliance_calendar import ComplianceCalendarService
from .services.talent_review import TalentReviewService
from .services.settings import HRMSettingsService

@module_access('hrm')
def index(request):
    # HR Overview / Dashboard
    try:
        employees = list(db.collection('hrm_employees').stream())
        positions = list(db.collection('org_positions').stream())

        total_emp = len(employees)
        active_emp = len([e for e in employees if (e.to_dict() or {}).get('status') == 'Active'])
        leave_emp = len([e for e in employees if (e.to_dict() or {}).get('status') == 'On Leave'])
        open_positions = len(positions)
        
        # Calculate pending approvals
        pending_leaves = len(list(db.collection('hrm_leaves').where('status', '==', 'Pending').stream()))
        pending_advances = len(list(db.collection('hrm_advances').where('status', '==', 'Pending').stream()))
        pending_claims = len(list(db.collection('hrm_expense_claims').where('status', '==', 'Pending').stream()))
        pending_approvals = pending_leaves + pending_advances + pending_claims

        # Calculate absenteeism rate
        from datetime import datetime
        today_str = datetime.now().strftime('%Y-%m-%d')
        today_att = [a.to_dict() or {} for a in db.collection('hrm_attendance').where('date', '==', today_str).stream()]
        absent_count = sum(1 for a in today_att if a.get('status') == 'Absent')
        total_att = len(today_att)
        absenteeism_rate = round((absent_count / total_att * 100), 1) if total_att > 0 else 0.0
        
        # Disciplinary KPIs
        try:
            from .models import DisciplinaryCase, DisciplinaryHearing
            open_cases = DisciplinaryCase.objects.filter(is_active=True).exclude(status__in=['Resolved', 'Dismissed']).count()
            now = timezone.now()
            upcoming_hearings = DisciplinaryHearing.objects.filter(
                is_active=True, status='Scheduled', hearing_date__gte=now
            ).count()
            recent_cases = list(
                DisciplinaryCase.objects.filter(is_active=True)
                .select_related('employee')
                .order_by('-created_at')[:5]
                .values('case_number', 'employee__name', 'nature_of_offense', 'severity', 'status')
            )
        except Exception:
            open_cases = 0
            upcoming_hearings = 0
            recent_cases = []

        recent_activities = [
            f"Employee database check completed.",
            f"Dashboard metrics refreshed.",
        ]
        if pending_approvals > 0:
            recent_activities.append(f"There are {pending_approvals} requests pending manager approval.")
        if open_cases > 0:
            recent_activities.append(f"{open_cases} open disciplinary case(s) require attention.")
    except Exception as e:
        hrm_logger.error(f"Error loading dashboard: {e}")
        total_emp, active_emp, leave_emp, open_positions = 0, 0, 0, 0
        pending_approvals = 0
        absenteeism_rate = 0.0
        open_cases = 0
        upcoming_hearings = 0
        recent_cases = []
        recent_activities = []

    context = {
        'total_employees': total_emp,
        'active_employees': active_emp,
        'employees_on_leave': leave_emp,
        'open_positions': open_positions,
        'pending_approvals': pending_approvals,
        'absenteeism_rate': absenteeism_rate,
        'open_cases': open_cases,
        'upcoming_hearings': upcoming_hearings,
        'recent_cases': recent_cases,
        'recent_activities': recent_activities
    }
    return render(request, 'hrm/overview.html', context)

@module_access('hrm')
def recruitment(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_candidate':
            errors = validate_candidate_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:recruitment')
            try:
                result = RecruitmentService.add_candidate(request.POST, request.user)
                msg = 'updated' if result == 'updated' else 'registered'
                messages.success(request, f"Candidate profile {msg} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding candidate: {e}")

        elif action == 'add_shortlist':
            try:
                result = RecruitmentService.add_shortlist(request.POST, request.user)
                if result == 'updated':
                    messages.success(request, "Shortlist details updated successfully.")
                elif result == 'created':
                    messages.success(request, "Candidate added to shortlist successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding shortlist candidate: {e}")

        elif action == 'add_interview':
            try:
                result = RecruitmentService.add_interview(request.POST, request.user)
                if result == 'updated':
                    messages.success(request, "Interview schedule updated successfully.")
                elif result == 'created':
                    messages.success(request, "Interview scheduled successfully.")
            except Exception as e:
                hrm_logger.error(f"Error scheduling interview: {e}")

        elif action == 'add_selection':
            try:
                result = RecruitmentService.add_selection(request.POST, request.user)
                if result == 'updated':
                    messages.success(request, "Selection details updated successfully.")
                elif result == 'created':
                    messages.success(request, "Selection decision logged successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving selection: {e}")

        elif action.startswith('delete_'):
            doc_id = request.POST.get('doc_id')
            try:
                RecruitmentService.delete_record(action, doc_id)
                messages.success(request, "Record deleted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error deleting: {e}")

        elif action == 'update_status':
            doc_id = request.POST.get('doc_id')
            new_status = request.POST.get('status')
            if doc_id and new_status:
                try:
                    RecruitmentService.update_status(doc_id, new_status, request.user)
                    messages.success(request, f"Candidate status updated to {new_status}.")
                except Exception as e:
                    hrm_logger.error(f"Error updating status: {e}")

        return redirect('hrm:recruitment')

    candidates, shortlists, interviews, selections, positions, departments, sub_departments = RecruitmentService.get_candidates()
    return render(request, 'hrm/recruitment.html', {
        'candidates': candidates,
        'shortlists': shortlists,
        'interviews': interviews,
        'selections': selections,
        'positions': positions,
        'departments': departments,
        'sub_departments': sub_departments
    })

@module_access('hrm')
def department(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_department':
            errors = validate_department_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:department')
            try:
                result = DepartmentService.add_department(request.POST, request.user)
                msg = 'updated' if result == 'updated' else 'added'
                messages.success(request, f"Department {msg} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding department: {e}")

        elif action == 'add_sub_department':
            try:
                result = DepartmentService.add_sub_department(request.POST, request.user)
                if result == 'updated':
                    messages.success(request, "Sub-department updated successfully.")
                elif result == 'created':
                    messages.success(request, "Sub-department added successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding sub department: {e}")

        elif action == 'add_position':
            errors = validate_position_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:department')
            try:
                result = DepartmentService.add_position(request.POST, request.user)
                if result == 'updated':
                    messages.success(request, "Job position updated successfully.")
                elif result == 'created':
                    messages.success(request, "Job position added successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding position: {e}")

        elif action.startswith('delete_'):
            doc_id = request.POST.get('doc_id')
            try:
                DepartmentService.delete_record(action, doc_id)
                messages.success(request, "Record deleted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error deleting: {e}")

        invalidate_cache('org_departments')
        invalidate_cache('org_departments_sub')
        invalidate_cache('org_positions')
        return redirect('hrm:department')

    departments = get_cached_collection('org_departments')
    for d in departments:
        linking = d.get('module_linking', [])
        if isinstance(linking, str):
            d['module_linking'] = [linking] if linking else []
        elif not isinstance(linking, list):
            d['module_linking'] = []

    sub_departments = get_cached_collection('org_departments_sub')
    positions = get_cached_collection('org_positions')

    return render(request, 'hrm/departments.html', {
        'departments': departments,
        'sub_departments': sub_departments,
        'positions': positions
    })

@module_access('hrm')
def employee_database(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete_employee':
            doc_id = request.POST.get('doc_id')
            try:
                EmployeeService.delete(doc_id)
                messages.success(request, "Employee record deleted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error deleting employee: {e}")
            return redirect('hrm:employee_database')

        errors = validate_employee_data(request.POST)
        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect('hrm:employee_database')

        try:
            result = EmployeeService.save_employee(request.POST, request.user)
            msg = 'updated' if result == 'updated' else 'registered'
            messages.success(request, f"Employee profile {msg} successfully.")
        except Exception as e:
            hrm_logger.error(f"Error saving employee: {e}")
        return redirect('hrm:employee_database')

    employees, departments, sub_departments, positions = EmployeeService.get_employee_context()
    return render(request, 'hrm/employee_database.html', {
        'employees': employees,
        'departments': departments,
        'sub_departments': sub_departments,
        'positions': positions
    })

@module_access('hrm')
def attendance(request):
    if request.method == 'POST':
        att_action = request.POST.get('att_action')

        if att_action == 'delete':
            doc_id = request.POST.get('doc_id')
            try:
                AttendanceService.delete(doc_id)
                messages.success(request, "Attendance record deleted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error deleting attendance: {e}")

        elif att_action == 'resolve_missing':
            errors = validate_attendance_data({
                'name': request.POST.get('missing_name'),
                'date': request.POST.get('missing_date'),
                'status': request.POST.get('corrected_status', 'Present'),
            })
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:attendance')
            try:
                AttendanceService.resolve_missing(request.POST, request.user)
                messages.success(request, "Missing attendance resolved successfully.")
            except Exception as e:
                hrm_logger.error(f"Error resolving missing attendance: {e}")

        else:
            errors = validate_attendance_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:attendance')
            try:
                AttendanceService.record_attendance(request.POST, request.user)
                messages.success(request, "Attendance record logged successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding attendance log: {e}")

        return redirect('hrm:attendance')

    logs, employees, missing_logs = AttendanceService.get_attendance_context()
    return render(request, 'hrm/attendance.html', {
        'logs': logs,
        'employees': employees,
        'missing_logs': missing_logs
    })

@module_access('hrm')
def leave(request):
    if request.method == 'POST':
        lv_action = request.POST.get('lv_action')

        if lv_action == 'add_holiday':
            errors = validate_holiday_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:leave')
            try:
                result = LeaveService.add_holiday(request.POST, request.user)
                msg = 'updated' if result == 'updated' else 'added'
                messages.success(request, f"Holiday {msg} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding holiday: {e}")

        elif lv_action == 'delete_holiday':
            doc_id = request.POST.get('doc_id')
            try:
                LeaveService.delete_holiday(doc_id)
                messages.success(request, "Holiday deleted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error deleting holiday: {e}")

        elif lv_action == 'apply_leave':
            errors = validate_leave_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:leave')
            try:
                result = LeaveService.apply_leave(request.POST, request.user)
                msg = 'updated' if result == 'updated' else 'submitted'
                messages.success(request, f"Leave request {msg} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error applying leave: {e}")

        elif lv_action in ('Approved', 'Rejected'):
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    LeaveService.approve_or_reject(doc_id, lv_action, request.user)
                    messages.success(request, f"Leave request status updated to {lv_action}.")
                except Exception as e:
                    hrm_logger.error(f"Error updating leave: {e}")

        elif lv_action == 'delete_leave':
            doc_id = request.POST.get('doc_id')
            try:
                LeaveService.delete(doc_id)
                messages.success(request, "Leave request deleted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error deleting leave: {e}")

        elif lv_action == 'save_weekend':
            weekend_days = request.POST.getlist('weekend_days')
            try:
                LeaveService.save_weekend(weekend_days)
                messages.success(request, "Weekend settings saved successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving weekend: {e}")

        return redirect('hrm:leave')

    holidays, leaves, employees, weekend_days, emp_balances = LeaveService.get_leave_context()
    return render(request, 'hrm/leave.html', {
        'holidays': holidays,
        'leaves': leaves,
        'employees': employees,
        'weekend_days': weekend_days,
        'all_days': ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
        'emp_balances': emp_balances,
    })

@module_access('hrm')
def payroll(request):
    if request.method == 'POST':
        pr_action = request.POST.get('pr_action')

        if pr_action == 'add_advance':
            errors = validate_advance_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:payroll')
            try:
                result = PayrollService.add_advance(request.POST, request.user)
                msg = 'updated' if result == 'updated' else 'filed'
                messages.success(request, f"Advance salary request {msg} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding advance salary: {e}")

        elif pr_action == 'delete_advance':
            doc_id = request.POST.get('doc_id')
            try:
                PayrollService.delete_advance(doc_id)
                messages.success(request, "Advance salary request deleted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error deleting advance: {e}")

        elif pr_action == 'generate_salary':
            try:
                result = PayrollService.generate_salary(request.POST, request.user)
                msg = 'updated/recalculated' if result == 'updated' else 'generated'
                messages.success(request, f"Payroll sheet {msg} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error generating payroll: {e}")

        elif pr_action == 'delete_payroll':
            doc_id = request.POST.get('doc_id')
            try:
                PayrollService.delete(doc_id)
                messages.success(request, "Payroll sheet deleted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error deleting payroll: {e}")

        elif pr_action == 'disburse_payroll':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    result = PayrollService.disburse_payroll(doc_id, request.user)
                    if result:
                        messages.success(request, "Payroll disbursed and journal entries posted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error disbursing payroll: {e}")

        return redirect('hrm:payroll')

    advances, payrolls, employees, months, years = PayrollService.get_payroll_context()
    return render(request, 'hrm/payroll.html', {
        'advances': advances,
        'payrolls': payrolls,
        'employees': employees,
        'months': months,
        'years': years
    })

@login_required
@module_access('hrm')
def get_payslip(request):
    emp_name = request.GET.get('employee')
    month_name = request.GET.get('month')
    year = request.GET.get('year')
    
    if not emp_name or not month_name or not year:
        return JsonResponse({'error': 'Missing parameters'}, status=400)
        
    months_map = {
        'January': '01', 'February': '02', 'March': '03', 'April': '04',
        'May': '05', 'June': '06', 'July': '07', 'August': '08',
        'September': '09', 'October': '10', 'November': '11', 'December': '12'
    }
    month_num = months_map.get(month_name)
    if not month_num:
        return JsonResponse({'error': 'Invalid month'}, status=400)
        
    target_period = f"{year}-{month_num}"
    
    try:
        # 1. Fetch employee
        emp_query = list(db.collection('hrm_employees').where('name', '==', emp_name).stream())
        if not emp_query:
            return JsonResponse({'error': 'Employee not found'}, status=404)
        emp_data = emp_query[0].to_dict()
        
        basic_salary = float(emp_data.get('basic_salary', 0))
        house_rent = float(emp_data.get('house_rent', 0))
        medical_allowance = float(emp_data.get('medical_allowance', 0))
        gross_salary = float(emp_data.get('gross_salary', 0))
        
        # 2. Count absent days from hrm_attendance
        absent_count = 0
        att_docs = db.collection('hrm_attendance').where('name', '==', emp_name).stream()
        for doc in att_docs:
            data = doc.to_dict()
            att_date = data.get('date', '')
            status = data.get('status', '')
            if att_date.startswith(target_period) and status == 'Absent':
                absent_count += 1
                
        # Calculate absent deduction: (basic_salary / 30) * absent_count
        daily_rate = basic_salary / 30.0 if basic_salary > 0 else 0.0
        absent_deduction = round(daily_rate * absent_count, 2)
        
        # 3. Fetch advances for this month
        advance_deduction = 0.0
        adv_docs = db.collection('hrm_advances').where('employee', '==', emp_name).where('deduct_month', '==', target_period).stream()
        for doc in adv_docs:
            data = doc.to_dict()
            advance_deduction += float(data.get('amount', 0))
            
        # Tax deduction (5% of basic salary)
        tax_deduction = round(basic_salary * 0.05, 2)
        
        # Net Pay calculation
        net_pay = round(gross_salary - absent_deduction - advance_deduction - tax_deduction, 2)
        if net_pay < 0:
            net_pay = 0.0
            
        return JsonResponse({
            'employee': emp_name,
            'period': f"{month_name} {year}",
            'basic_salary': basic_salary,
            'house_rent': house_rent,
            'medical_allowance': medical_allowance,
            'absent_days': absent_count,
            'absent_deduction': absent_deduction,
            'advance_deduction': advance_deduction,
            'tax_deduction': tax_deduction,
            'net_pay': net_pay
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@module_access('hrm')
def reports(request):
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': d.to_dict().get('name', '')} for d in emp_docs if d.to_dict().get('name')]
    except Exception:
        employees = []

    context = {
        'employees': employees,
        'report_data': None,
        'report_type': None
    }

    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        employee_filter = request.POST.get('employee_filter')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        context['report_type'] = report_type

        try:
            if report_type == 'Attendance Summary':
                att_docs = db.collection('hrm_attendance').stream()
                att_records = [d.to_dict() for d in att_docs]

                summary = {}
                for r in att_records:
                    # Field stored during attendance recording is 'name', not 'employee'
                    emp_name = r.get('name', '')
                    if not emp_name: continue
                    if employee_filter != 'All Employees' and emp_name != employee_filter: continue

                    r_date = r.get('date', '')
                    if start_date and r_date < start_date: continue
                    if end_date and r_date > end_date: continue

                    if emp_name not in summary:
                        summary[emp_name] = {'Present': 0, 'Absent': 0, 'Late': 0, 'Half Day': 0}

                    status = r.get('status', '')
                    if status in summary[emp_name]:
                        summary[emp_name][status] += 1

                rows = [[name, data['Present'], data['Absent'], data['Late'], data['Half Day']] for name, data in summary.items()]

                context['report_data'] = {
                    'headers': ['Employee', 'Total Present', 'Total Absent', 'Total Late', 'Total Half Day'],
                    'rows': rows
                }

            elif report_type == 'Payroll Summary':
                emp_data = {}
                for e in db.collection('hrm_employees').stream():
                    dt = e.to_dict()
                    name = dt.get('name')
                    if name:
                        # Fallback to a default 0 if basic_salary not found
                        emp_data[name] = float(dt.get('basic_salary', 0))

                adv_docs = db.collection('hrm_advances').stream()
                advances = {}
                for doc in adv_docs:
                    d = doc.to_dict()
                    if d.get('status') == 'Deducted': continue
                    emp_name = d.get('employee')
                    advances[emp_name] = advances.get(emp_name, 0) + float(d.get('amount', 0))

                rows = []
                for name, b_pay in emp_data.items():
                    if employee_filter != 'All Employees' and name != employee_filter: continue
                    adv = advances.get(name, 0)
                    net = b_pay - adv
                    rows.append([name, f"${b_pay:,.2f}", f"${adv:,.2f}", f"${net:,.2f}"])

                context['report_data'] = {
                    'headers': ['Employee', 'Basic Pay', 'Pending Advances', 'Estimated Net Pay'],
                    'rows': rows
                }

            elif report_type == 'Leave History':
                leave_docs = db.collection('hrm_leaves').stream()
                rows = []
                for doc in leave_docs:
                    d = doc.to_dict()
                    emp_name = d.get('name', '')
                    if not emp_name: continue
                    if employee_filter != 'All Employees' and emp_name != employee_filter: continue

                    l_from = d.get('from_date', '')
                    l_to = d.get('to_date', '')
                    
                    if start_date and l_to < start_date: continue
                    if end_date and l_from > end_date: continue

                    rows.append([
                        emp_name, 
                        d.get('type', ''), 
                        d.get('duration', ''), 
                        d.get('status', 'Pending')
                    ])

                context['report_data'] = {
                    'headers': ['Employee', 'Leave Type', 'Duration', 'Status'],
                    'rows': rows
                }

        except Exception as e:
            hrm_logger.error(f"Error generating report: {e}")

    return render(request, 'hrm/reports.html', context)


@login_required
@module_access('hrm')
def onboarding_offboarding(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_task':
            try:
                OnboardingService.add_task(request.POST, request.user)
                messages.success(request, "Onboarding task added successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding onboarding task: {e}")

        elif action == 'complete_task':
            if doc_id:
                try:
                    OnboardingService.update_status(doc_id, 'Completed', request.user)
                    messages.success(request, "Onboarding task marked as completed.")
                except Exception as e:
                    hrm_logger.error(f"Error completing onboarding task: {e}")

        elif action == 'delete_task':
            if doc_id:
                try:
                    OnboardingService.delete(doc_id)
                    messages.success(request, "Onboarding task deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting onboarding task: {e}")

        elif action == 'trigger_exit':
            try:
                emp_name = request.POST.get('employee')
                OnboardingService.add_exit_clearance(request.POST, request.user)
                emp_query = list(db.collection('hrm_employees').where('name', '==', emp_name).stream())
                if emp_query:
                    emp_query[0].reference.update(
                        enrich_with_audit({'status': 'Resigned'}, request.user, is_update=True)
                    )
                messages.success(request, "Exit clearance workflow triggered successfully.")
            except Exception as e:
                hrm_logger.error(f"Error triggering exit: {e}")

        elif action == 'update_clearance':
            if doc_id:
                try:
                    field = request.POST.get('clearance_field')
                    status = request.POST.get('clearance_status')
                    OnboardingService.update_clearance(doc_id, field, status, request.user)

                    doc_snap = db.collection('hrm_exit_clearance').document(doc_id).get().to_dict()
                    if doc_snap and all(doc_snap.get(f) == 'Cleared' for f in ('it_clearance', 'finance_clearance', 'hr_clearance')):
                        db.collection('hrm_exit_clearance').document(doc_id).update(
                            enrich_with_audit({'status': 'Cleared'}, request.user, is_update=True)
                        )
                        emp_name = doc_snap.get('employee')
                        emp_query = list(db.collection('hrm_employees').where('name', '==', emp_name).stream())
                        if emp_query:
                            emp_query[0].reference.update(
                                enrich_with_audit({'status': 'Inactive'}, request.user, is_update=True)
                            )
                    messages.success(request, "Exit clearance status updated successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error updating clearance: {e}")

        return redirect('hrm:onboarding_offboarding')

    tasks = get_collection_data('hrm_onboarding_tasks', [])
    exits = get_collection_data('hrm_exit_clearance', [])
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', '')} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    return render(request, 'hrm/onboarding_offboarding.html', {
        'tasks': tasks,
        'exits': exits,
        'employees': employees
    })


@login_required
@module_access('hrm')
def roster_management(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'assign_shift':
            errors = validate_shift_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:roster_management')
            try:
                RosterService.assign_shift(request.POST, request.user)
                messages.success(request, "Employee shift roster assigned successfully.")
            except Exception as e:
                hrm_logger.error(f"Error assigning shift: {e}")

        elif action == 'delete_shift':
            if doc_id:
                try:
                    RosterService.delete(doc_id)
                    messages.success(request, "Shift assignment deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting shift: {e}")

        return redirect('hrm:roster_management')

    shifts = get_collection_data('hrm_employee_shifts', [])
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', '')} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    return render(request, 'hrm/roster_management.html', {
        'shifts': shifts,
        'employees': employees
    })


@login_required
@module_access('hrm')
def expense_claims(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'file_claim':
            errors = validate_expense_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:expense_claims')
            try:
                ExpenseService.file_claim(request.POST, request.user)
                messages.success(request, "Expense claim filed successfully.")
            except Exception as e:
                hrm_logger.error(f"Error filing expense claim: {e}")

        elif action == 'approve_claim':
            if doc_id:
                try:
                    ExpenseService.approve_claim(doc_id, request.user)
                    messages.success(request, "Expense claim approved successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error approving claim: {e}")

        elif action == 'reject_claim':
            if doc_id:
                try:
                    ExpenseService.reject_claim(doc_id, request.user)
                    messages.success(request, "Expense claim rejected.")
                except Exception as e:
                    hrm_logger.error(f"Error rejecting claim: {e}")

        elif action == 'delete_claim':
            if doc_id:
                try:
                    ExpenseService.delete(doc_id)
                    messages.success(request, "Expense claim deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting claim: {e}")

        return redirect('hrm:expense_claims')

    claims = get_collection_data('hrm_expense_claims', [])
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', '')} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    return render(request, 'hrm/expense_claims.html', {
        'claims': claims,
        'employees': employees
    })


@login_required
@module_access('hrm')
def document_asset_vault(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_document':
            errors = validate_document_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:document_asset_vault')
            try:
                DocumentAssetService.add_document(request.POST, request.user)
                messages.success(request, "Employee document added to vault successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding document: {e}")

        elif action == 'delete_document':
            if doc_id:
                try:
                    DocumentAssetService.delete_document(doc_id)
                    messages.success(request, "Employee document deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting document: {e}")

        elif action == 'assign_asset':
            errors = validate_asset_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:document_asset_vault')
            try:
                DocumentAssetService.assign_asset(request.POST, request.user)
                messages.success(request, "Asset assigned to employee successfully.")
            except Exception as e:
                hrm_logger.error(f"Error assigning asset: {e}")

        elif action == 'return_asset':
            if doc_id:
                try:
                    DocumentAssetService.return_asset(doc_id, request.user)
                    messages.success(request, "Asset marked as returned successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error returning asset: {e}")

        elif action == 'delete_asset':
            if doc_id:
                try:
                    db.collection('hrm_assets').document(doc_id).delete()
                    messages.success(request, "Asset record deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting asset: {e}")

        return redirect('hrm:document_asset_vault')

    documents = get_collection_data('hrm_documents', [])
    assets = get_collection_data('hrm_assets', [])
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', '')} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    return render(request, 'hrm/document_asset_vault.html', {
        'documents': documents,
        'assets': assets,
        'employees': employees
    })


@login_required
@module_access('hrm')
def performance(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_review_cycle':
            try:
                result = PerformanceService.add_review_cycle(request.POST, request.user)
                msg = 'updated' if result == 'updated' else 'created'
                messages.success(request, f"Review cycle {msg} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving review cycle: {e}")

        elif action == 'delete_review_cycle':
            doc_id = request.POST.get('doc_id')
            try:
                PerformanceService.delete_record(action, doc_id)
                messages.success(request, "Review cycle deleted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error deleting review cycle: {e}")

        elif action == 'add_kpi':
            try:
                result = PerformanceService.add_kpi(request.POST, request.user)
                msg = 'updated' if result == 'updated' else 'created'
                messages.success(request, f"KPI {msg} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving KPI: {e}")

        elif action == 'delete_kpi':
            doc_id = request.POST.get('doc_id')
            try:
                PerformanceService.delete_record(action, doc_id)
                messages.success(request, "KPI deleted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error deleting KPI: {e}")

        elif action == 'add_review':
            try:
                result = PerformanceService.add_review(request.POST, request.user)
                msg = 'updated' if result == 'updated' else 'created'
                messages.success(request, f"Performance review {msg} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving review: {e}")

        elif action == 'delete_review':
            doc_id = request.POST.get('doc_id')
            try:
                PerformanceService.delete_record(action, doc_id)
                messages.success(request, "Performance review deleted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error deleting review: {e}")

        elif action == 'add_pip':
            try:
                result = PerformanceService.add_pip(request.POST, request.user)
                msg = 'updated' if result == 'updated' else 'created'
                messages.success(request, f"PIP {msg} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving PIP: {e}")

        elif action == 'delete_pip':
            doc_id = request.POST.get('doc_id')
            try:
                PerformanceService.delete_record(action, doc_id)
                messages.success(request, "PIP deleted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error deleting PIP: {e}")

        return redirect('hrm:performance')

    review_cycles = get_collection_data('hrm_review_cycles', [])
    kpis = get_collection_data('hrm_kpis', [])
    reviews = get_collection_data('hrm_performance_reviews', [])
    pips = get_collection_data('hrm_pips', [])
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', '')} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    return render(request, 'hrm/performance.html', {
        'review_cycles': review_cycles, 'kpis': kpis,
        'reviews': reviews, 'pips': pips, 'employees': employees,
    })


# ── Disciplinary Management ─────────────────────────────────────────

@login_required
@module_access('hrm')
def disciplinary(request):
    from hrm.models import Employee as SQLEmployee
    from .validators import validate_disciplinary_data, validate_hearing_data, validate_action_data, validate_appeal_data

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_case':
            errors = validate_disciplinary_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:disciplinary')
            try:
                result = DisciplineService.add_case(request.POST, request.user)
                messages.success(request, f"Disciplinary case {'updated' if result == 'updated' else 'created'} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving disciplinary case: {e}")
                messages.error(request, "Failed to save disciplinary case.")

        elif action == 'delete_case':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    from hrm.models import DisciplinaryCase
                    DisciplinaryCase.objects.filter(id=doc_id).update(is_active=False)
                    messages.success(request, "Disciplinary case removed.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting case: {e}")

        elif action == 'add_hearing':
            errors = validate_hearing_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:disciplinary')
            try:
                result = DisciplineService.add_hearing(request.POST, request.user)
                if result:
                    messages.success(request, f"Hearing {'updated' if result == 'updated' else 'scheduled'} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving hearing: {e}")

        elif action == 'delete_hearing':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    from hrm.models import DisciplinaryHearing
                    DisciplinaryHearing.objects.filter(id=doc_id).update(is_active=False)
                    messages.success(request, "Hearing removed.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting hearing: {e}")

        elif action == 'add_action':
            errors = validate_action_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:disciplinary')
            try:
                result = DisciplineService.add_action(request.POST, request.user)
                if result:
                    messages.success(request, f"Action {'updated' if result == 'updated' else 'issued'} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error saving action: {e}")

        elif action == 'add_appeal':
            errors = validate_appeal_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:disciplinary')
            try:
                result = DisciplineService.add_appeal(request.POST, request.user)
                if result:
                    messages.success(request, "Appeal submitted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error submitting appeal: {e}")

        elif action == 'resolve_appeal':
            appeal_id = request.POST.get('appeal_id')
            decision = request.POST.get('decision')
            if appeal_id and decision:
                try:
                    DisciplineService.resolve_appeal(appeal_id, decision, request.POST, request.user)
                    messages.success(request, f"Appeal {decision.lower()}.")
                except Exception as e:
                    hrm_logger.error(f"Error resolving appeal: {e}")

        elif action == 'close_case':
            case_id = request.POST.get('case_id')
            resolution = request.POST.get('resolution', '')
            resolved_date = request.POST.get('resolved_date')
            if case_id:
                try:
                    DisciplineService.close_case(case_id, resolution, resolved_date, request.user)
                    messages.success(request, "Case closed as resolved.")
                except Exception as e:
                    hrm_logger.error(f"Error closing case: {e}")

        return redirect('hrm:disciplinary')

    context = DisciplineService.get_case_context()
    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', ''), 'id': d.id} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    try:
        sql_employees = SQLEmployee.objects.filter(is_active=True).values('id', 'name', 'emp_id')
    except Exception:
        sql_employees = []

    context['employees'] = employees
    context['sql_employees'] = sql_employees
    return render(request, 'hrm/discipline.html', context)


# ── Notification Center (Admin) ───────────────────────────────────────

@login_required
@module_access('hrm')
def notification_center(request):
    from hrm.models import Notification

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'mark_read':
            nid = request.POST.get('notification_id')
            if nid:
                NotifService.mark_read(nid, request.user)
                messages.success(request, "Notification marked as read.")
        elif action == 'mark_all_read':
            NotifService.mark_all_read(request.user)
            messages.success(request, "All notifications marked as read.")
        elif action == 'update_prefs':
            NotifService.update_preferences(request.user, request.POST)
            messages.success(request, "Notification preferences updated.")
        return redirect('hrm:notification_center')

    notifications = NotifService.get_notifications(request.user)
    unread_count = NotifService.get_unread_count(request.user)
    from hrm.models import NotificationPreference
    pref, _ = NotificationPreference.objects.get_or_create(user=request.user)

    return render(request, 'hrm/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
        'prefs': pref,
    })


# ── Succession Planning (Admin) ───────────────────────────────────────

@login_required
@module_access('hrm')
def succession_planning(request):
    from hrm.models import KeyPosition, SuccessorCandidate, SuccessionPlan

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_key_position':
            try:
                result = SuccessionService.add_key_position(request.POST)
                messages.success(request, "Key position added successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding key position: {e}")
                messages.error(request, "Failed to add key position.")

        elif action == 'update_key_position':
            try:
                result = SuccessionService.add_key_position(request.POST)
                messages.success(request, "Key position updated successfully.")
            except Exception as e:
                hrm_logger.error(f"Error updating key position: {e}")

        elif action == 'add_successor':
            try:
                result = SuccessionService.add_successor(request.POST)
                if result:
                    messages.success(request, "Successor candidate added successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding successor: {e}")

        elif action == 'update_successor':
            try:
                result = SuccessionService.add_successor(request.POST)
                messages.success(request, "Successor candidate updated.")
            except Exception as e:
                hrm_logger.error(f"Error updating successor: {e}")

        elif action == 'delete_successor':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                SuccessorCandidate.objects.filter(id=doc_id).update(is_active=False)
                messages.success(request, "Successor candidate removed.")

        elif action == 'create_plan':
            try:
                result = SuccessionService.add_plan(request.POST)
                messages.success(request, "Succession plan created successfully.")
            except Exception as e:
                hrm_logger.error(f"Error creating succession plan: {e}")

        elif action == 'delete_position':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                KeyPosition.objects.filter(id=doc_id).update(is_active=False)
                messages.success(request, "Key position removed.")

        return redirect('hrm:succession_planning')

    key_positions = KeyPosition.objects.filter(is_active=True).select_related('position')
    successors = SuccessorCandidate.objects.filter(is_active=True).select_related('key_position', 'employee')
    plans = SuccessionPlan.objects.filter(is_active=True)

    try:
        emp_docs = db.collection('hrm_employees').stream()
        employees = [{'name': (d.to_dict() or {}).get('name', ''), 'id': d.id} for d in emp_docs if (d.to_dict() or {}).get('name')]
    except Exception:
        employees = []

    positions = get_cached_collection('org_positions')
    departments = get_cached_collection('org_departments')

    return render(request, 'hrm/succession.html', {
        'key_positions': key_positions, 'successors': successors,
        'plans': plans, 'employees': employees,
        'positions': positions, 'departments': departments,
    })


# ── Unread Count (AJAX) ───────────────────────────────────────────────

@login_required
def get_unread_notification_count(request):
    from hrm.models import Notification
    count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    return JsonResponse({'count': count})


# ── Phase 5: Skills Inventory ──────────────────────────────────────

@login_required
@module_access('hrm')
def skills_inventory(request):
    from hrm.models import (
        Employee as SQLEmployee, EmployeeEducation, EmployeeExperience,
        EmployeeSkill, Competency, CompetencyRating,
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'add_education':
                SkillsService.add_education(request.POST)
                messages.success(request, "Education record added.")
            elif action == 'add_experience':
                SkillsService.add_experience(request.POST)
                messages.success(request, "Experience record added.")
            elif action == 'add_skill':
                SkillsService.add_skill(request.POST)
                messages.success(request, "Skill added.")
            elif action == 'add_competency_rating':
                SkillsService.add_competency_rating(request.POST)
                messages.success(request, "Competency rating saved.")
        except Exception as e:
            hrm_logger.error(f"Skills inventory error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:skills_inventory')

    employees = SQLEmployee.objects.filter(is_active=True)
    education = EmployeeEducation.objects.filter(is_active=True).select_related('employee')
    experiences = EmployeeExperience.objects.filter(is_active=True).select_related('employee')
    skills = EmployeeSkill.objects.filter(is_active=True).select_related('employee')
    competencies = Competency.objects.filter(is_active=True)
    competency_ratings = CompetencyRating.objects.filter(is_active=True).select_related('employee', 'competency', 'assessed_by')

    return render(request, 'hrm/skills_inventory.html', {
        'employees': employees, 'education': education, 'experiences': experiences,
        'skills': skills, 'competencies': competencies, 'competency_ratings': competency_ratings,
    })


# ── Phase 5: 360 Feedback ──────────────────────────────────────────

@login_required
@module_access('hrm')
def feedback_360(request):
    from hrm.models import (
        Employee as SQLEmployee, ReviewCycle,
        FeedbackQuestion, FeedbackRequest, FeedbackResponse,
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'add_question':
                FeedbackService.add_question(request.POST)
                messages.success(request, "Feedback question added.")
            elif action == 'send_request':
                FeedbackService.add_request(request.POST)
                messages.success(request, "Feedback request sent.")
        except Exception as e:
            hrm_logger.error(f"360 feedback error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:feedback_360')

    questions = FeedbackQuestion.objects.filter(is_active=True)
    requests = FeedbackRequest.objects.filter(is_active=True).select_related('reviewer', 'reviewee', 'review_cycle')
    responses = FeedbackResponse.objects.select_related('request', 'question')
    employees = SQLEmployee.objects.filter(is_active=True)
    cycles = ReviewCycle.objects.filter(is_active=True)

    return render(request, 'hrm/feedback_360.html', {
        'questions': questions, 'requests': requests, 'responses': responses,
        'employees': employees, 'cycles': cycles,
    })


# ── Phase 5: Engagement Surveys ────────────────────────────────────

@login_required
@module_access('hrm')
def engagement_surveys(request):
    from hrm.models import (
        EngagementSurvey, SurveyQuestion, SurveyResponse,
        Employee as SQLEmployee,
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'create_survey':
                SurveyService.add_survey(request.POST)
                messages.success(request, "Survey created successfully.")
            elif action == 'add_question':
                survey = EngagementSurvey.objects.get(id=request.POST.get('survey_id'))
                SurveyQuestion.objects.create(
                    survey=survey,
                    question_text=request.POST['question_text'],
                    question_type=request.POST.get('question_type', 'text'),
                    is_required=request.POST.get('is_required') == 'on',
                    order=int(request.POST.get('order', 0)),
                )
                messages.success(request, "Survey question added.")
        except Exception as e:
            hrm_logger.error(f"Survey error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:engagement_surveys')

    surveys = EngagementSurvey.objects.filter(is_active=True)
    survey_questions = SurveyQuestion.objects.filter(is_active=True).select_related('survey')
    survey_responses = SurveyResponse.objects.select_related('survey', 'question', 'employee')

    return render(request, 'hrm/engagement_surveys.html', {
        'surveys': surveys, 'survey_questions': survey_questions,
        'survey_responses': survey_responses,
    })


# ── Phase 5: Compliance Calendar ────────────────────────────────────

@login_required
@module_access('hrm')
def compliance_calendar(request):
    from hrm.models import Employee as SQLEmployee, ComplianceReminder
    from hrm.services import sync_document_compliance_reminders, check_compliance_overdue_reminders

    sync_document_compliance_reminders()
    check_compliance_overdue_reminders()

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'add_reminder':
                ComplianceCalendarService.add_reminder(request.POST)
                messages.success(request, "Compliance reminder added.")
            elif action == 'complete_reminder':
                reminder = ComplianceReminder.objects.get(id=request.POST.get('reminder_id'))
                reminder.mark_completed()
                messages.success(request, f"Reminder '{reminder.title}' marked complete.")
            elif action == 'dismiss_reminder':
                ComplianceReminder.objects.filter(id=request.POST.get('reminder_id')).update(is_active=False)
                messages.success(request, "Reminder dismissed.")
        except Exception as e:
            hrm_logger.error(f"Compliance calendar error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:compliance_calendar')

    reminders = ComplianceReminder.objects.filter(is_active=True).select_related('employee')
    employees = SQLEmployee.objects.filter(is_active=True)
    upcoming = reminders.filter(status__in=['Pending', 'Overdue']).order_by('due_date')

    return render(request, 'hrm/compliance_calendar.html', {
        'reminders': reminders, 'employees': employees, 'upcoming': upcoming,
    })


# ── Phase 5: Talent Review & 9-Box ──────────────────────────────────

@login_required
@module_access('hrm')
def talent_review(request):
    from hrm.models import Employee as SQLEmployee, TalentReviewMeeting, NineBoxCell

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'start_meeting':
                TalentReviewService.add_meeting(request.POST)
                messages.success(request, "Talent review meeting created.")
            elif action == 'add_cell':
                TalentReviewService.set_nine_box(request.POST)
                messages.success(request, "9-Box cell added.")
            elif action == 'complete_meeting':
                TalentReviewMeeting.objects.filter(id=request.POST.get('meeting_id')).update(status='Completed')
                messages.success(request, "Meeting marked as completed.")
        except Exception as e:
            hrm_logger.error(f"Talent review error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:talent_review')

    meetings = TalentReviewMeeting.objects.filter(is_active=True)
    cells = NineBoxCell.objects.filter(is_active=True).select_related('employee', 'talent_review')
    employees = SQLEmployee.objects.filter(is_active=True)

    return render(request, 'hrm/talent_review.html', {
        'meetings': meetings, 'cells': cells, 'employees': employees,
    })


# ── Configuration UI ───────────────────────────────────────────────

@login_required
@module_access('hrm')
def hrm_settings(request):
    from hrm.models import HRMSetting, LeavePolicy, RatingTemplate, RatingScale

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'update_setting':
                HRMSettingsService.save_setting(request.POST.get('key'), request.POST.get('value', ''))
                messages.success(request, f"Setting updated.")
            elif action == 'add_setting':
                HRMSettingsService.save_setting(request.POST.get('key'), request.POST.get('value', ''))
                messages.success(request, "Setting created.")
            elif action == 'delete_setting':
                HRMSetting.objects.filter(id=request.POST.get('setting_id')).update(is_active=False)
                messages.success(request, "Setting removed.")
            elif action == 'add_leave_policy':
                HRMSettingsService.add_leave_policy(request.POST)
                messages.success(request, "Leave policy added.")
            elif action == 'delete_leave_policy':
                LeavePolicy.objects.filter(id=request.POST.get('policy_id')).update(is_active=False)
                messages.success(request, "Leave policy removed.")
            elif action == 'add_rating_template':
                HRMSettingsService.add_rating_template(request.POST)
                messages.success(request, "Rating template created.")
            elif action == 'add_rating_scale':
                template = RatingTemplate.objects.get(id=request.POST.get('template_id'))
                RatingScale.objects.create(
                    template=template,
                    label=request.POST['label'],
                    value=request.POST['value'],
                    definition=request.POST.get('definition', ''),
                    order=int(request.POST.get('order', 0)),
                )
                messages.success(request, "Rating scale value added.")
        except Exception as e:
            hrm_logger.error(f"Settings error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:hrm_settings')

    settings = HRMSetting.objects.filter(is_active=True)
    leave_policies = LeavePolicy.objects.filter(is_active=True)
    templates = RatingTemplate.objects.filter(is_active=True).prefetch_related('scales')

    return render(request, 'hrm/hrm_settings.html', {
        'settings': settings,
        'leave_policies': leave_policies,
        'templates': templates,
    })

def employee_cases_json(request, emp_id):
    from .models import Employee as SQLEmployee
    from .models import DisciplinaryCase, DisciplinaryHearing, DisciplinaryAction
    try:
        employee = SQLEmployee.objects.filter(emp_id=emp_id, is_active=True).first()
        if not employee:
            return JsonResponse({'cases': [], 'error': None})
        cases = DisciplinaryCase.objects.filter(
            employee=employee, is_active=True
        ).select_related('reported_by').order_by('-created_at')
        data = []
        for c in cases:
            hearings = list(
                DisciplinaryHearing.objects.filter(case=c, is_active=True).values(
                    'hearing_date', 'status', 'outcome'
                )
            )
            actions = list(
                DisciplinaryAction.objects.filter(case=c, is_active=True).values(
                    'action_type', 'issued_date', 'status'
                )
            )
            data.append({
                'case_number': c.case_number,
                'nature_of_offense': c.nature_of_offense,
                'severity': c.severity,
                'status': c.status,
                'incident_date': str(c.incident_date) if c.incident_date else None,
                'resolution': c.resolution,
                'hearings': hearings,
                'actions': actions,
            })
        return JsonResponse({'cases': data, 'error': None})
    except Exception as e:
        hrm_logger.error(f"Error fetching employee cases: {e}")
        return JsonResponse({'cases': [], 'error': str(e)})

