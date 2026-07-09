import json
from datetime import datetime, date, timedelta
from collections import defaultdict
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from config.firebase import db
from google.cloud import firestore
from accounts.decorators import module_access
from config.logger import hrm_logger


def _firestore_count(collection_name, field=None, value=None):
    try:
        docs = db.collection(collection_name).stream()
        if field and value:
            return sum(1 for d in docs if (d.to_dict() or {}).get(field) == value)
        return sum(1 for _ in docs)
    except Exception:
        return 0


@module_access('hrm')
def dashboard(request):
    """High-level HRM analytics dashboard with cross-module KPIs and charts."""
    from config.services.kpi_service import KPIService

    kpi_data = KPIService.get_cross_module_kpis()

    try:
        employees = list(db.collection('hrm_employees').stream())
        total_emp = len(employees)
        active_emp = sum(1 for e in employees if (e.to_dict() or {}).get('status') == 'Active')
        dept_dist = defaultdict(int)
        for e in employees:
            dept = (e.to_dict() or {}).get('department', 'Unknown')
            dept_dist[dept] += 1
        dept_labels = list(dept_dist.keys())
        dept_counts = list(dept_dist.values())
    except Exception as e:
        hrm_logger.error(f"Analytics dashboard error: {e}")
        total_emp = active_emp = 0
        dept_labels = dept_counts = []

    try:
        today = date.today()
        month_prefix = today.strftime('%Y-%m')
        att_docs = list(db.collection('hrm_attendance').stream())
        present = sum(1 for d in att_docs if (d.to_dict() or {}).get('date', '').startswith(month_prefix) and (d.to_dict() or {}).get('status') == 'Present')
        absent = sum(1 for d in att_docs if (d.to_dict() or {}).get('date', '').startswith(month_prefix) and (d.to_dict() or {}).get('status') == 'Absent')
        late = sum(1 for d in att_docs if (d.to_dict() or {}).get('date', '').startswith(month_prefix) and (d.to_dict() or {}).get('status') == 'Late')
    except Exception:
        present = absent = late = 0

    try:
        leave_docs = list(db.collection('hrm_leaves').stream())
        pending_leaves = sum(1 for l in leave_docs if (l.to_dict() or {}).get('status') == 'Pending')
        approved_leaves = sum(1 for l in leave_docs if (l.to_dict() or {}).get('status') == 'Approved')
        leave_by_type = defaultdict(int)
        for l in leave_docs:
            lt = (l.to_dict() or {}).get('type', 'Other')
            leave_by_type[lt] += 1
        leave_type_labels = list(leave_by_type.keys())
        leave_type_counts = list(leave_by_type.values())
    except Exception:
        pending_leaves = approved_leaves = 0
        leave_type_labels = leave_type_counts = []

    try:
        trn_docs = list(db.collection('trn_registrations').stream())
        trn_reg_count = len(trn_docs)
        trn_paid = sum(1 for d in trn_docs if (d.to_dict() or {}).get('payment_status') in ['Fully Paid', 'Partially Paid'])
        trn_unpaid = sum(1 for d in trn_docs if (d.to_dict() or {}).get('payment_status') in ['Unpaid', ''])
    except Exception:
        trn_reg_count = trn_paid = trn_unpaid = 0

    context = {
        'total_employees': total_emp,
        'active_employees': active_emp,
        'present_count': present,
        'absent_count': absent,
        'late_count': late,
        'pending_leaves': pending_leaves,
        'approved_leaves': approved_leaves,
        'trn_reg_count': trn_reg_count,
        'trn_paid': trn_paid,
        'trn_unpaid': trn_unpaid,
        'dept_labels_json': json.dumps(dept_labels),
        'dept_counts_json': json.dumps(dept_counts),
        'leave_type_labels_json': json.dumps(leave_type_labels),
        'leave_type_counts_json': json.dumps(leave_type_counts),
    }
    return render(request, 'hrm/analytics/dashboard.html', context)


@module_access('hrm')
def workforce(request):
    """Workforce analytics: headcount, department distribution, turnover trends."""
    try:
        employees = list(db.collection('hrm_employees').stream())
        emp_list = []
        for e in employees:
            d = e.to_dict()
            d['id'] = e.id
            emp_list.append(d)
        total = len(emp_list)
        active = sum(1 for e in emp_list if e.get('status') == 'Active')
        on_leave = sum(1 for e in emp_list if e.get('status') == 'On Leave')
        resigned = sum(1 for e in emp_list if e.get('status') == 'Resigned')

        type_dist = defaultdict(int)
        dept_dist = defaultdict(int)
        for e in emp_list:
            type_dist[e.get('employee_type', 'Other')] += 1
            dept_dist[e.get('department', 'Unknown')] += 1

        gender_dist = defaultdict(int)
        for e in emp_list:
            gender_dist[e.get('gender', 'Other')] += 1
    except Exception as e:
        hrm_logger.error(f"Workforce analytics error: {e}")
        emp_list = []
        total = active = on_leave = resigned = 0
        type_dist = dept_dist = gender_dist = defaultdict(int)

    context = {
        'total': total,
        'active': active,
        'on_leave': on_leave,
        'resigned': resigned,
        'type_labels_json': json.dumps(list(type_dist.keys())),
        'type_counts_json': json.dumps(list(type_dist.values())),
        'dept_labels_json': json.dumps(list(dept_dist.keys())),
        'dept_counts_json': json.dumps(list(dept_dist.values())),
        'gender_labels_json': json.dumps(list(gender_dist.keys())),
        'gender_counts_json': json.dumps(list(gender_dist.values())),
    }
    return render(request, 'hrm/analytics/workforce.html', context)


@module_access('hrm')
def training(request):
    """Training analytics: enrollments, revenue, completion rates."""
    try:
        courses = list(db.collection('trn_courses').stream())
        course_names = [c.to_dict().get('title', c.to_dict().get('name', 'Unnamed')) for c in courses]

        registrations = list(db.collection('trn_registrations').stream())
        total_reg = len(registrations)
        course_reg = defaultdict(list)
        for r in registrations:
            rd = r.to_dict()
            cname = rd.get('course', 'Unknown')
            course_reg[cname].append(rd)
    except Exception as e:
        hrm_logger.error(f"Training analytics error: {e}")
        course_names = []
        registrations = []
        total_reg = 0
        course_reg = defaultdict(list)

    try:
        payments = list(db.collection('trn_payments').stream())
        total_collected = sum(float(p.to_dict().get('amount_paid', 0)) for p in payments)
        total_due = sum(float(p.to_dict().get('due_amount', 0)) for p in payments)
        fully_paid = sum(1 for p in payments if p.to_dict().get('status') == 'Fully Paid')
        partially_paid = sum(1 for p in payments if p.to_dict().get('status') == 'Partially Paid')
        unpaid = sum(1 for p in payments if p.to_dict().get('status') in ['Unpaid', ''])
    except Exception:
        total_collected = total_due = fully_paid = partially_paid = unpaid = 0

    try:
        assessments = list(db.collection('trn_assessments').stream())
        passed = sum(1 for a in assessments if a.to_dict().get('status') == 'Passed')
        failed = sum(1 for a in assessments if a.to_dict().get('status') == 'Failed')
        total_assessed = sum(1 for a in assessments if a.to_dict().get('status') in ['Passed', 'Failed'])
    except Exception:
        passed = failed = total_assessed = 0

    try:
        placements = list(db.collection('trn_job_placements').stream())
        total_placed = len(placements)
    except Exception:
        total_placed = 0

    course_reg_counts = [len(course_reg.get(c, [])) for c in course_names]

    context = {
        'total_courses': len(course_names),
        'total_registrations': total_reg,
        'total_collected': total_collected,
        'total_due': total_due,
        'fully_paid': fully_paid,
        'partially_paid': partially_paid,
        'unpaid': unpaid,
        'passed': passed,
        'failed': failed,
        'total_assessed': total_assessed,
        'total_placed': total_placed,
        'course_labels_json': json.dumps(course_names),
        'course_counts_json': json.dumps(course_reg_counts),
    }
    return render(request, 'hrm/analytics/training.html', context)
