from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models as orm_models
from accounts.decorators import module_access
from config.workflow_integration import ensure_workflow, try_transition, LEAVE_TRIGGER_MAP
from config.logger import hrm_logger
from datetime import datetime, date
from django.utils import timezone
from .validators import (
    validate_employee_data, validate_attendance_data, validate_leave_data,
    validate_candidate_data, validate_department_data, validate_position_data,
    validate_advance_data, validate_expense_data, validate_shift_data,
    validate_document_data, validate_asset_data, validate_holiday_data,
)
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

from .models import (
    Employee, Department, Position, Attendance, Leave, Holiday, AdvanceSalary,
    Payroll, PayrollEmployee, EmployeeShift, OnboardingTask, ExitClearance,
    ExpenseClaim, Document, Asset, DisciplinaryCase, DisciplinaryHearing,
    DisciplinaryAction, DisciplinaryAppeal, ReviewCycle, KPI, PerformanceReview,
    PerformanceImprovementPlan, Notification, NotificationPreference,
    KeyPosition, SuccessorCandidate, SuccessionPlan, EmployeeEducation,
    EmployeeExperience, EmployeeSkill, Competency, CompetencyRating,
    FeedbackQuestion, FeedbackRequest, FeedbackResponse, EngagementSurvey,
    SurveyQuestion, SurveyResponse, ComplianceReminder, TalentReviewMeeting,
    NineBoxCell, HRMSetting, LeavePolicy, RatingTemplate, RatingScale,
)

months_map = {
    'January': '01', 'February': '02', 'March': '03', 'April': '04',
    'May': '05', 'June': '06', 'July': '07', 'August': '08',
    'September': '09', 'October': '10', 'November': '11', 'December': '12',
}
MONTH_CHOICES = list(months_map.keys())
YEAR_CHOICES = [str(y) for y in range(2020, 2035)]


def _emp_list():
    return [{'id': str(e.pk), 'first_name': e.first_name, 'last_name': e.last_name, 'name': e.name}
            for e in Employee.objects.filter(is_active=True)]


def _emp_dict_list():
    return [{'name': e.name, 'id': str(e.pk)} for e in Employee.objects.filter(is_active=True)]


# ── Index / Dashboard ────────────────────────────────────────────────

@module_access('hrm')
def index(request):
    try:
        total_emp = Employee.objects.count()
        active_emp = Employee.objects.filter(status='Active').count()
        leave_emp = Employee.objects.filter(status='On Leave').count()
        open_positions = Position.objects.filter(status='Active').count()

        pending_leaves = Leave.objects.filter(status='Pending').count()
        pending_advances = AdvanceSalary.objects.filter(status='Pending').count()
        pending_claims = ExpenseClaim.objects.filter(status='Pending').count()
        pending_approvals = pending_leaves + pending_advances + pending_claims

        today_att = Attendance.objects.filter(date=date.today())
        total_att = today_att.count()
        absent_count = today_att.filter(status='Absent').count()
        absenteeism_rate = round((absent_count / total_att * 100), 1) if total_att > 0 else 0.0

        open_cases = DisciplinaryCase.objects.filter(is_active=True).exclude(status__in=('Resolved', 'Dismissed')).count()
        upcoming_hearings = DisciplinaryHearing.objects.filter(status='Scheduled', case__is_active=True).count()
        recent_cases = list(DisciplinaryCase.objects.filter(is_active=True).order_by('-created_at').values(
            'case_number', 'employee__first_name', 'nature_of_offense', 'severity', 'status'
        )[:5])

        recent_activities = ["Employee database check completed.", "Dashboard metrics refreshed."]
        if pending_approvals > 0:
            recent_activities.append(f"There are {pending_approvals} requests pending manager approval.")
        if open_cases > 0:
            recent_activities.append(f"{open_cases} open disciplinary case(s) require attention.")
    except Exception as e:
        hrm_logger.error(f"Error loading dashboard: {e}")
        total_emp = active_emp = leave_emp = open_positions = 0
        pending_approvals = absenteeism_rate = 0
        open_cases = upcoming_hearings = 0
        recent_cases = []
        recent_activities = []

    context = {
        'total_employees': total_emp, 'active_employees': active_emp,
        'employees_on_leave': leave_emp, 'open_positions': open_positions,
        'pending_approvals': pending_approvals, 'absenteeism_rate': absenteeism_rate,
        'open_cases': open_cases, 'upcoming_hearings': upcoming_hearings,
        'recent_cases': recent_cases, 'recent_activities': recent_activities,
    }
    return render(request, 'hrm/overview.html', context)


# ── Recruitment ──────────────────────────────────────────────────────

@module_access('hrm')
def recruitment(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'add_candidate':
            errors = validate_candidate_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:recruitment')
            try:
                RecruitmentService.add_candidate(request.POST, request.user)
                messages.success(request, "Candidate added successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding candidate: {e}")

        elif action == 'add_shortlist':
            try:
                result = RecruitmentService.add_shortlist(request.POST, request.user)
                if result:
                    messages.success(request, "Candidate shortlisted successfully.")
            except Exception as e:
                hrm_logger.error(f"Error shortlisting: {e}")

        elif action == 'update_stage':
            if doc_id:
                new_stage = request.POST.get('new_stage')
                try:
                    RecruitmentService.update_stage(doc_id, new_stage, request.user)
                    messages.success(request, "Candidate stage updated.")
                except Exception as e:
                    hrm_logger.error(f"Error updating stage: {e}")

        elif action == 'delete_candidate':
            if doc_id:
                try:
                    RecruitmentService.delete(doc_id)
                    messages.success(request, "Candidate record deleted.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting candidate: {e}")

        elif action == 'schedule_interview':
            try:
                result = RecruitmentService.schedule_interview(request.POST, request.user)
                if result:
                    messages.success(request, "Interview scheduled successfully.")
            except Exception as e:
                hrm_logger.error(f"Error scheduling interview: {e}")

        elif action == 'delete_interview':
            if doc_id:
                try:
                    RecruitmentService.delete_interview(doc_id)
                    messages.success(request, "Interview record deleted.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting interview: {e}")

        elif action == 'add_selection':
            try:
                RecruitmentService.add_selection(request.POST, request.user)
                messages.success(request, "Candidate selected and offer recorded.")
            except Exception as e:
                hrm_logger.error(f"Error adding selection: {e}")

        elif action == 'delete_selection':
            if doc_id:
                try:
                    RecruitmentService.delete_selection(doc_id)
                    messages.success(request, "Selection record deleted.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting selection: {e}")

        return redirect('hrm:recruitment')

    candidates, shortlists, interviews, selections = RecruitmentService.get_candidates()
    return render(request, 'hrm/recruitment.html', {
        'candidates': candidates, 'shortlists': shortlists,
        'interviews': interviews, 'selections': selections,
    })


# ── Department & Positions ───────────────────────────────────────────

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
                msg = 'updated' if result == 'updated' else 'created'
                messages.success(request, f"Department {msg} successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding department: {e}")

        elif action == 'add_sub_department':
            errors = validate_department_data(request.POST)
            if errors:
                for e in errors:
                    messages.error(request, e)
                return redirect('hrm:department')
            try:
                result = DepartmentService.add_sub_department(request.POST, request.user)
                msg = 'updated' if result == 'updated' else 'created'
                messages.success(request, f"Sub-department {msg} successfully.")
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

        return redirect('hrm:department')

    departments = list(Department.objects.filter(parent__isnull=True, is_active=True).values(
        'id', 'name', 'module_linking', 'notes', 'status', 'is_active',
    ))
    for d in departments:
        linking = d.get('module_linking', [])
        if isinstance(linking, str):
            d['module_linking'] = [linking] if linking else []
        elif not isinstance(linking, list):
            d['module_linking'] = []

    sub_departments = list(Department.objects.filter(parent__isnull=False, is_active=True).values(
        'id', 'name', 'parent__name', 'module_linking', 'notes', 'status', 'is_active',
    ))
    positions = list(Position.objects.filter(is_active=True).select_related('department', 'sub_department').values(
        'id', 'title', 'department__name', 'sub_department__name', 'status', 'is_active',
    ))

    return render(request, 'hrm/departments.html', {
        'departments': departments,
        'sub_departments': sub_departments,
        'positions': positions,
    })


# ── Employee Database ────────────────────────────────────────────────

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
        'positions': positions,
    })


# ── Attendance ───────────────────────────────────────────────────────

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
        'missing_logs': missing_logs,
    })


# ── Leave & Holidays ─────────────────────────────────────────────────

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


# ── Payroll & Advances ───────────────────────────────────────────────

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
        'advances': advances, 'payrolls': payrolls,
        'employees': employees, 'months': months, 'years': years,
    })


# ── Payslip AJAX ─────────────────────────────────────────────────────

@login_required
@module_access('hrm')
def get_payslip(request):
    emp_name = request.GET.get('employee')
    month_name = request.GET.get('month')
    year = request.GET.get('year')

    if not emp_name or not month_name or not year:
        return JsonResponse({'error': 'Missing parameters'}, status=400)

    month_num = months_map.get(month_name)
    if not month_num:
        return JsonResponse({'error': 'Invalid month'}, status=400)

    target_period = f"{year}-{month_num}"

    try:
        emp = Employee.objects.filter(name=emp_name, is_active=True).first()
        if not emp:
            return JsonResponse({'error': 'Employee not found'}, status=404)

        basic_salary = float(emp.basic_salary or 0)
        house_rent = float(emp.house_rent or 0)
        medical_allowance = float(emp.medical_allowance or 0)
        gross_salary = float(emp.gross_salary or 0)

        absent_count = Attendance.objects.filter(
            employee=emp, date__startswith=target_period, status='Absent'
        ).count()

        daily_rate = basic_salary / 30.0 if basic_salary > 0 else 0.0
        absent_deduction = round(daily_rate * absent_count, 2)

        advance_deduction = float(
            AdvanceSalary.objects.filter(
                employee=emp, deduct_month=target_period, is_active=True
            ).exclude(status='Deducted').aggregate(total=orm_models.Sum('amount'))['total'] or 0
        )

        tax_deduction = round(basic_salary * 0.05, 2)

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
            'net_pay': net_pay,
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── Reports ──────────────────────────────────────────────────────────

@module_access('hrm')
def reports(request):
    try:
        employees = [{'name': e.name} for e in Employee.objects.filter(is_active=True) if e.name]
    except Exception:
        employees = []

    context = {'employees': employees, 'report_data': None, 'report_type': None}

    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        employee_filter = request.POST.get('employee_filter')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        context['report_type'] = report_type

        try:
            if report_type == 'Attendance Summary':
                qs = Attendance.objects.filter(is_active=True).select_related('employee')
                summary = {}
                for r in qs:
                    emp_name = r.employee.name
                    if not emp_name:
                        continue
                    if employee_filter != 'All Employees' and emp_name != employee_filter:
                        continue
                    r_date = str(r.date)
                    if start_date and r_date < start_date:
                        continue
                    if end_date and r_date > end_date:
                        continue
                    summary.setdefault(emp_name, {'Present': 0, 'Absent': 0, 'Late': 0, 'Half Day': 0})
                    if r.status in summary[emp_name]:
                        summary[emp_name][r.status] += 1

                rows = [[name, data['Present'], data['Absent'], data['Late'], data['Half Day']]
                        for name, data in summary.items()]
                context['report_data'] = {
                    'headers': ['Employee', 'Total Present', 'Total Absent', 'Total Late', 'Total Half Day'],
                    'rows': rows,
                }

            elif report_type == 'Payroll Summary':
                emp_data = {}
                for e in Employee.objects.filter(is_active=True):
                    name = e.name
                    if name:
                        emp_data[name] = float(e.basic_salary or 0)

                advances = {}
                adv_qs = AdvanceSalary.objects.filter(is_active=True)
                for a in adv_qs:
                    if a.status == 'Deducted':
                        continue
                    emp_name = a.employee.name
                    advances[emp_name] = advances.get(emp_name, 0) + float(a.amount or 0)

                rows = []
                for name, b_pay in emp_data.items():
                    if employee_filter != 'All Employees' and name != employee_filter:
                        continue
                    adv = advances.get(name, 0)
                    net = b_pay - adv
                    rows.append([name, f"${b_pay:,.2f}", f"${adv:,.2f}", f"${net:,.2f}"])

                context['report_data'] = {
                    'headers': ['Employee', 'Basic Pay', 'Pending Advances', 'Estimated Net Pay'],
                    'rows': rows,
                }

            elif report_type == 'Leave History':
                leave_qs = Leave.objects.filter(is_active=True).select_related('employee')
                rows = []
                for d in leave_qs:
                    emp_name = d.employee.name
                    if not emp_name:
                        continue
                    if employee_filter != 'All Employees' and emp_name != employee_filter:
                        continue
                    l_from = str(d.from_date)
                    l_to = str(d.to_date)
                    if start_date and l_to < start_date:
                        continue
                    if end_date and l_from > end_date:
                        continue
                    rows.append([emp_name, d.leave_type, d.duration or '', d.status])

                context['report_data'] = {
                    'headers': ['Employee', 'Leave Type', 'Duration', 'Status'],
                    'rows': rows,
                }

        except Exception as e:
            hrm_logger.error(f"Error generating report: {e}")

    return render(request, 'hrm/reports.html', context)


# ── Onboarding & Offboarding ─────────────────────────────────────────

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
                emp = Employee.objects.filter(name=emp_name).first()
                if emp:
                    emp.status = 'Resigned'
                    emp.save(update_fields=['status'])
                messages.success(request, "Exit clearance workflow triggered successfully.")
            except Exception as e:
                hrm_logger.error(f"Error triggering exit: {e}")

        elif action == 'update_clearance':
            if doc_id:
                try:
                    field = request.POST.get('clearance_field')
                    status_val = request.POST.get('clearance_status')
                    OnboardingService.update_clearance(doc_id, field, status_val, request.user)

                    clearance = ExitClearance.objects.filter(pk=doc_id, is_active=True).first()
                    if clearance:
                        if all(getattr(clearance, f, '') == 'Cleared' for f in ('it_clearance', 'finance_clearance', 'hr_clearance')):
                            clearance.status = 'Cleared'
                            clearance.save(update_fields=['status'])
                            emp = clearance.employee
                            emp.status = 'Inactive'
                            emp.save(update_fields=['status'])
                    messages.success(request, "Exit clearance status updated successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error updating clearance: {e}")

        return redirect('hrm:onboarding_offboarding')

    tasks = list(OnboardingTask.objects.filter(is_active=True).select_related('employee').values(
        'id', 'employee__name', 'task_name', 'due_date', 'status', 'is_active',
    ))
    exits = list(ExitClearance.objects.filter(is_active=True).select_related('employee').values(
        'id', 'employee__name', 'exit_date', 'reason', 'it_clearance', 'finance_clearance', 'hr_clearance', 'status',
    ))
    employees = _emp_list()

    return render(request, 'hrm/onboarding_offboarding.html', {
        'tasks': tasks, 'exits': exits, 'employees': employees,
    })


# ── Roster / Shift Management ────────────────────────────────────────

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

    shifts = list(EmployeeShift.objects.filter(is_active=True).select_related('employee').values(
        'id', 'employee__name', 'shift_name', 'start_date', 'end_date', 'is_active',
    ))
    employees = _emp_list()

    return render(request, 'hrm/roster_management.html', {
        'shifts': shifts, 'employees': employees,
    })


# ── Expense Claims ───────────────────────────────────────────────────

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

    claims = list(ExpenseClaim.objects.filter(is_active=True).select_related('employee').values(
        'id', 'employee__name', 'category', 'amount', 'description', 'status', 'created_at',
    ))
    employees = _emp_list()

    return render(request, 'hrm/expense_claims.html', {
        'claims': claims, 'employees': employees,
    })


# ── Document & Asset Vault ───────────────────────────────────────────

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
                    Asset.objects.filter(pk=doc_id).update(is_active=False)
                    messages.success(request, "Asset record deleted successfully.")
                except Exception as e:
                    hrm_logger.error(f"Error deleting asset: {e}")

        return redirect('hrm:document_asset_vault')

    documents = list(Document.objects.filter(is_active=True).select_related('employee').values(
        'id', 'employee__name', 'document_type', 'document_number', 'expiry_date', 'file',
    ))
    assets = list(Asset.objects.filter(is_active=True).select_related('employee').values(
        'id', 'employee__name', 'asset_name', 'asset_tag', 'serial_number', 'status',
    ))
    employees = _emp_list()

    return render(request, 'hrm/document_asset_vault.html', {
        'documents': documents, 'assets': assets, 'employees': employees,
    })


# ── Performance Management ───────────────────────────────────────────

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

    review_cycles = list(ReviewCycle.objects.filter(is_active=True).values(
        'id', 'name', 'start_date', 'end_date', 'review_type', 'status',
    ))
    kpis = list(KPI.objects.filter(is_active=True).values(
        'id', 'name', 'description', 'unit', 'target_value', 'default_weight',
    ))
    reviews = list(PerformanceReview.objects.filter(is_active=True).select_related('employee', 'reviewer', 'review_cycle').values(
        'id', 'employee__name', 'reviewer__first_name', 'review_cycle__name', 'overall_score', 'status',
    ))
    pips = list(PerformanceImprovementPlan.objects.filter(is_active=True).select_related('employee').values(
        'id', 'employee__name', 'issue_description', 'start_date', 'end_date', 'status',
    ))
    employees = _emp_list()

    return render(request, 'hrm/performance.html', {
        'review_cycles': review_cycles, 'kpis': kpis,
        'reviews': reviews, 'pips': pips, 'employees': employees,
    })


# ── Disciplinary Management ─────────────────────────────────────────

@login_required
@module_access('hrm')
def disciplinary(request):
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
                    DisciplinaryCase.objects.filter(pk=doc_id).update(is_active=False)
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
            hearing_id = request.POST.get('doc_id')
            if hearing_id:
                try:
                    DisciplinaryHearing.objects.filter(pk=hearing_id).update(is_active=False)
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

    cases = list(DisciplinaryCase.objects.filter(is_active=True).select_related('employee').values(
        'id', 'employee__name', 'case_number', 'incident_date', 'nature_of_offense',
        'severity', 'status', 'resolution', 'resolved_date',
    ))
    for c in cases:
        c_id = c.pop('id', None)
        if c_id:
            c['hearings'] = list(DisciplinaryHearing.objects.filter(case_id=c_id, is_active=True).values(
                'id', 'hearing_date', 'panel_members', 'location', 'status', 'outcome',
            ))
            c['actions'] = list(DisciplinaryAction.objects.filter(case_id=c_id, is_active=True).values(
                'id', 'action_type', 'description', 'issued_date', 'status',
            ))
            appeals = []
            for a in DisciplinaryAction.objects.filter(case_id=c_id, is_active=True):
                appeals.extend(
                    DisciplinaryAppeal.objects.filter(action=a, is_active=True).values(
                        'id', 'action__action_type', 'appeal_date', 'grounds', 'status',
                    )
                )
            c['appeals'] = appeals

    employees = _emp_dict_list()

    return render(request, 'hrm/discipline.html', {
        'cases': cases, 'employees': employees,
    })


# ── Notification Center ──────────────────────────────────────────────

@login_required
@module_access('hrm')
def notification_center(request):
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

    pref, _ = NotificationPreference.objects.get_or_create(
        user=request.user,
        defaults={
            'notify_in_app': True,
            'notify_email': True,
            'notify_push': False,
            'digest_frequency': 'instant',
        }
    )

    return render(request, 'hrm/notifications.html', {
        'notifications': notifications,
        'unread_count': unread_count,
        'prefs': pref,
    })


# ── Succession Planning ──────────────────────────────────────────────

@login_required
@module_access('hrm')
def succession_planning(request):
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_key_position':
            try:
                SuccessionService.add_key_position(request.POST)
                messages.success(request, "Key position added successfully.")
            except Exception as e:
                hrm_logger.error(f"Error adding key position: {e}")
                messages.error(request, "Failed to add key position.")

        elif action == 'update_key_position':
            try:
                SuccessionService.add_key_position(request.POST)
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
                SuccessionService.add_successor(request.POST)
                messages.success(request, "Successor candidate updated.")
            except Exception as e:
                hrm_logger.error(f"Error updating successor: {e}")

        elif action == 'delete_successor':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                SuccessorCandidate.objects.filter(pk=doc_id).update(is_active=False)
                messages.success(request, "Successor candidate removed.")

        elif action == 'create_plan':
            try:
                SuccessionService.add_plan(request.POST)
                messages.success(request, "Succession plan created successfully.")
            except Exception as e:
                hrm_logger.error(f"Error creating succession plan: {e}")

        elif action == 'delete_position':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                KeyPosition.objects.filter(pk=doc_id).update(is_active=False)
                messages.success(request, "Key position removed.")

        return redirect('hrm:succession_planning')

    key_positions = list(KeyPosition.objects.filter(is_active=True).select_related('position', 'department', 'incumbent').values(
        'id', 'position_title', 'position__title', 'department__name', 'incumbent__name', 'risk_of_vacancy', 'status',
    ))
    successors = list(SuccessorCandidate.objects.filter(is_active=True).select_related('key_position', 'employee').values(
        'id', 'key_position__position_title', 'employee__name', 'readiness', 'is_primary', 'notes',
    ))
    plans = list(SuccessionPlan.objects.filter(is_active=True).select_related('department').values(
        'id', 'title', 'description', 'department__name', 'review_date', 'status',
    ))
    employees = _emp_dict_list()

    positions_list = list(Position.objects.filter(is_active=True).values('id', 'title'))
    departments_list = list(Department.objects.filter(is_active=True).values('id', 'name'))

    return render(request, 'hrm/succession.html', {
        'key_positions': key_positions, 'successors': successors,
        'plans': plans, 'employees': employees,
        'positions': positions_list, 'departments': departments_list,
    })


# ── Unread Count (AJAX) ──────────────────────────────────────────────

@login_required
def get_unread_notification_count(request):
    count = NotifService.get_unread_count(request.user)
    return JsonResponse({'count': count})


# ── Skills Inventory ──────────────────────────────────────────────────

@login_required
@module_access('hrm')
def skills_inventory(request):
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

    employees = _emp_list()
    education = list(EmployeeEducation.objects.filter(is_active=True).select_related('employee').values(
        'id', 'employee__name', 'degree', 'institution', 'field_of_study', 'start_year', 'end_year', 'grade',
    ))
    experiences = list(EmployeeExperience.objects.filter(is_active=True).select_related('employee').values(
        'id', 'employee__name', 'company', 'job_title', 'start_date', 'end_date', 'is_current', 'description',
    ))
    skills = list(EmployeeSkill.objects.filter(is_active=True).select_related('employee').values(
        'id', 'employee__name', 'skill_name', 'proficiency', 'years_of_experience',
    ))
    competencies = list(Competency.objects.filter(is_active=True).values('id', 'name', 'category', 'description'))
    competency_ratings = list(CompetencyRating.objects.filter(is_active=True).select_related('employee', 'competency').values(
        'id', 'employee__name', 'competency__name', 'rating', 'assessment_date', 'notes',
    ))

    return render(request, 'hrm/skills_inventory.html', {
        'employees': employees, 'education': education, 'experiences': experiences,
        'skills': skills, 'competencies': competencies, 'competency_ratings': competency_ratings,
    })


# ── 360 Feedback ──────────────────────────────────────────────────────

@login_required
@module_access('hrm')
def feedback_360(request):
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

    questions = list(FeedbackQuestion.objects.filter(is_active=True).values(
        'id', 'category', 'question_text', 'is_required', 'order',
    ))
    requests = list(FeedbackRequest.objects.filter(is_active=True).select_related('reviewee', 'review_cycle').values(
        'id', 'reviewer', 'reviewee__name', 'review_cycle__name', 'relationship', 'status', 'due_date',
    ))
    responses = list(FeedbackResponse.objects.select_related('request', 'question').values(
        'id', 'request__id', 'question__question_text', 'rating', 'response_text',
    ))
    employees = _emp_list()
    cycles = list(ReviewCycle.objects.filter(is_active=True).values('id', 'name'))

    return render(request, 'hrm/feedback_360.html', {
        'questions': questions, 'requests': requests, 'responses': responses,
        'employees': employees, 'cycles': cycles,
    })


# ── Engagement Surveys ────────────────────────────────────────────────

@login_required
@module_access('hrm')
def engagement_surveys(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'create_survey':
                SurveyService.add_survey(request.POST)
                messages.success(request, "Survey created successfully.")
            elif action == 'add_question':
                survey_id = request.POST.get('survey_id')
                try:
                    survey = EngagementSurvey.objects.get(pk=survey_id)
                except EngagementSurvey.DoesNotExist:
                    messages.error(request, "Survey not found.")
                    return redirect('hrm:engagement_surveys')
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

    surveys = list(EngagementSurvey.objects.filter(is_active=True).values(
        'id', 'title', 'description', 'start_date', 'end_date', 'is_anonymous', 'status',
    ))
    survey_questions = list(SurveyQuestion.objects.filter(is_active=True).select_related('survey').values(
        'id', 'survey__title', 'question_text', 'question_type', 'is_required', 'order',
    ))
    survey_responses = list(SurveyResponse.objects.select_related('survey', 'question', 'employee').values(
        'id', 'survey__title', 'question__question_text', 'employee__name', 'response_text', 'response_value',
    ))

    return render(request, 'hrm/engagement_surveys.html', {
        'surveys': surveys, 'survey_questions': survey_questions,
        'survey_responses': survey_responses,
    })


# ── Compliance Calendar ──────────────────────────────────────────────

@login_required
@module_access('hrm')
def compliance_calendar(request):
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
                reminder_id = request.POST.get('reminder_id')
                now_date = timezone.now().date()
                ComplianceReminder.objects.filter(pk=reminder_id).update(
                    status='Completed', completed_date=now_date,
                )
                messages.success(request, "Reminder marked complete.")
            elif action == 'dismiss_reminder':
                ComplianceReminder.objects.filter(
                    pk=request.POST.get('reminder_id')
                ).update(is_active=False)
                messages.success(request, "Reminder dismissed.")
        except Exception as e:
            hrm_logger.error(f"Compliance calendar error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:compliance_calendar')

    reminders = list(ComplianceReminder.objects.filter(is_active=True).select_related('employee').values(
        'id', 'employee__name', 'reminder_type', 'title', 'description', 'due_date', 'completed_date', 'status',
    ))
    employees = _emp_list()
    upcoming = [r for r in reminders if r.get('status') in ('Pending', 'Overdue')]

    return render(request, 'hrm/compliance_calendar.html', {
        'reminders': reminders, 'employees': employees, 'upcoming': upcoming,
    })


# ── Talent Review & 9-Box ────────────────────────────────────────────

@login_required
@module_access('hrm')
def talent_review(request):
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
                meeting_id = request.POST.get('meeting_id')
                TalentReviewMeeting.objects.filter(pk=meeting_id).update(
                    status='Completed',
                )
                messages.success(request, "Meeting marked as completed.")
        except Exception as e:
            hrm_logger.error(f"Talent review error: {e}")
            messages.error(request, f"Error: {e}")
        return redirect('hrm:talent_review')

    meetings = list(TalentReviewMeeting.objects.filter(is_active=True).values(
        'id', 'title', 'meeting_date', 'notes', 'status',
    ))
    cells = list(NineBoxCell.objects.filter(is_active=True).select_related('employee', 'talent_review').values(
        'id', 'talent_review__title', 'employee__name', 'performance', 'potential', 'notes',
    ))
    employees = _emp_list()

    nine_box_levels = ['High', 'Medium', 'Low']
    return render(request, 'hrm/talent_review.html', {
        'meetings': meetings, 'cells': cells, 'employees': employees,
        'nine_box_levels': nine_box_levels,
    })


# ── Configuration UI ─────────────────────────────────────────────────

@login_required
@module_access('hrm')
def hrm_settings(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'update_setting':
                HRMSettingsService.save_setting(request.POST.get('key'), request.POST.get('value', ''))
                messages.success(request, "Setting updated.")
            elif action == 'add_setting':
                HRMSettingsService.save_setting(request.POST.get('key'), request.POST.get('value', ''))
                messages.success(request, "Setting created.")
            elif action == 'delete_setting':
                HRMSetting.objects.filter(pk=request.POST.get('setting_id')).update(is_active=False)
                messages.success(request, "Setting removed.")
            elif action == 'add_leave_policy':
                HRMSettingsService.add_leave_policy(request.POST)
                messages.success(request, "Leave policy added.")
            elif action == 'delete_leave_policy':
                LeavePolicy.objects.filter(pk=request.POST.get('policy_id')).update(is_active=False)
                messages.success(request, "Leave policy removed.")
            elif action == 'add_rating_template':
                HRMSettingsService.add_rating_template(request.POST)
                messages.success(request, "Rating template created.")
            elif action == 'add_rating_scale':
                template_id = request.POST.get('template_id')
                try:
                    template = RatingTemplate.objects.get(pk=template_id)
                except RatingTemplate.DoesNotExist:
                    messages.error(request, "Rating template not found.")
                    return redirect('hrm:hrm_settings')
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

    settings = list(HRMSetting.objects.filter(is_active=True).values('id', 'key', 'value'))
    leave_policies = list(LeavePolicy.objects.filter(is_active=True).values(
        'id', 'employee_type', 'leave_type', 'entitled_days', 'carry_forward_days',
    ))
    templates = list(RatingTemplate.objects.filter(is_active=True).values('id', 'name', 'description'))

    return render(request, 'hrm/hrm_settings.html', {
        'settings': settings,
        'leave_policies': leave_policies,
        'templates': templates,
    })


# ── Employee Cases JSON (AJAX) ───────────────────────────────────────

def employee_cases_json(request, emp_id):
    try:
        emp = Employee.objects.filter(emp_id=emp_id, is_active=True).first()
        if not emp:
            return JsonResponse({'cases': [], 'error': None})

        cases = DisciplinaryCase.objects.filter(employee=emp, is_active=True).order_by('-created_at')
        data = []
        for c in cases:
            hearings = list(c.hearings.filter(is_active=True).values('hearing_date', 'status', 'outcome'))
            actions = list(c.actions.filter(is_active=True).values('action_type', 'issued_date', 'status'))
            data.append({
                'case_number': c.case_number,
                'nature_of_offense': c.nature_of_offense,
                'severity': c.severity,
                'status': c.status,
                'incident_date': str(c.incident_date) if c.incident_date else None,
                'resolution': c.resolution or '',
                'hearings': list(hearings),
                'actions': list(actions),
            })
        return JsonResponse({'cases': data, 'error': None})
    except Exception as e:
        hrm_logger.error(f"Error fetching employee cases: {e}")
        return JsonResponse({'cases': [], 'error': str(e)})
