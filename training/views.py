from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from accounts.decorators import module_access
from config.logger import training_logger
import random
import re
import json
from datetime import datetime, date
from decimal import Decimal

from .models import (
    Course, Batch, Registration, Payment, Expense, Inquiry,
    Institute, Ambassador, Commission, Assessment, Certificate,
    JobPlacement, ClassSession, PaymentInstallment,
)
from hrm.models import Employee
from billing.models import ChartOfAccount, JournalEntry, JournalEntryLine


def _resolve(doc_id, model_class):
    if not doc_id:
        return None
    try:
        return model_class.objects.get(pk=doc_id)
    except (model_class.DoesNotExist, ValueError):
        pass
    return model_class.objects.filter(pk=doc_id).first()


def _model_to_dict(obj, extra_fields=None):
    """Convert a model instance to a dict with camelCase keys for template compatibility."""
    d = {}
    for field in obj._meta.get_fields():
        if hasattr(field, 'column') and field.concrete:
            val = getattr(obj, field.name, None)
            if isinstance(val, (datetime, date)):
                val = str(val)
            if isinstance(val, Decimal):
                val = float(val)
            if val is not None:
                key = field.name
                d[key] = val
    if extra_fields:
        d.update(extra_fields)
    d['id'] = obj.pk or str(obj.pk)
    return d


def _get_collection_data(model_class, filters=None, order_by=None, extra_fn=None):
    """ORM-based collection data fetcher."""
    qs = model_class.objects.filter(is_active=True)
    if filters:
        qs = qs.filter(**filters)
    if order_by:
        qs = qs.order_by(order_by)
    results = []
    for obj in qs:
        d = _model_to_dict(obj)
        if extra_fn:
            extra_fn(obj, d)
        results.append(d)
    return results


def generate_student_id(registrations_qs):
    max_serial = 0
    for r in registrations_qs:
        sid = r.student_id or ''
        match = re.search(r'(?:^|-)(495\d{3})$', sid)
        if match:
            num = int(match.group(1)[3:])
            if num > max_serial:
                max_serial = num
    next_serial = max_serial + 1
    return f"495{next_serial:03d}"


def log_training_action(user, action_type, collection_name, record_id, details):
    try:
        training_logger.info(f"[{action_type}] {collection_name}/{record_id}: {details} by {user}")
    except Exception as e:
        training_logger.error(f"Error logging action: {e}")


@login_required
@module_access('training')
def index(request):
    return redirect('training:overview')


@login_required
@module_access('training')
def overview(request):
    try:
        registrations = Registration.objects.filter(is_active=True)
        payments = Payment.objects.filter(is_active=True)
        expenses = Expense.objects.filter(is_active=True)
        placements = JobPlacement.objects.filter(is_active=True)
        batches = Batch.objects.filter(is_active=True)
        inquiries = Inquiry.objects.filter(is_active=True)
        commissions = Commission.objects.filter(is_active=True)
        courses = Course.objects.filter(is_active=True)
        employees = Employee.objects.all()

        total_students = len({r.student_id for r in registrations if r.student_id})
        total_collected = sum(float(p.amount_paid) for p in payments)
        total_due = sum(float(p.due_amount) for p in payments)
        total_discount = sum(float(p.discount) for p in payments)

        fully_paid_count = payments.filter(status='Fully Paid').count()
        partially_paid_count = payments.filter(status='Partially Paid').count()
        unpaid_count = payments.filter(status='Unpaid').count()

        total_expenses_val = sum(float(e.amount) for e in expenses)
        net_income = total_collected - total_expenses_val
        placed_students = placements.count()
        active_batches = batches.filter(status='Active').count()
        pending_inquiries = inquiries.filter(status='New').count()
        active_employees = employees.filter(status='Active').count()
        total_commissions = sum(float(c.payout_amount) for c in commissions)
        total_courses = courses.count()

        collection_rate = (total_collected / (total_collected + total_due) * 100) if (total_collected + total_due) > 0 else 0

        course_counts = {}
        for r in registrations:
            c = r.course.title if r.course else None
            if c:
                course_counts[c] = course_counts.get(c, 0) + 1

        monthly_collections = {}
        for p in payments:
            ca = p.created_at
            if ca:
                ym = ca.strftime('%Y-%m')
                monthly_collections[ym] = monthly_collections.get(ym, 0.0) + float(p.amount_paid)

        monthly_expenses = {}
        for e in expenses:
            dt = e.date
            if dt:
                ym = str(dt)[:7]
                monthly_expenses[ym] = monthly_expenses.get(ym, 0.0) + float(e.amount)

        all_months = sorted(list(set(monthly_collections.keys()) | set(monthly_expenses.keys())))

        course_revenue = {}
        for c in course_counts.keys():
            course_revenue[c] = {'collected': 0.0, 'due': 0.0}
        for p in payments:
            c = p.course.title if p.course else p.course_name
            if c:
                if c not in course_revenue:
                    course_revenue[c] = {'collected': 0.0, 'due': 0.0}
                course_revenue[c]['collected'] += float(p.amount_paid)
                course_revenue[c]['due'] += float(p.due_amount)

        chart_data = {
            'payment_status': [fully_paid_count, partially_paid_count, unpaid_count],
            'course_labels': list(course_counts.keys()),
            'course_data': list(course_counts.values()),
            'months': all_months,
            'month_collections': [monthly_collections.get(m, 0.0) for m in all_months],
            'month_expenses': [monthly_expenses.get(m, 0.0) for m in all_months],
            'rev_course_labels': list(course_revenue.keys()),
            'rev_collected_data': [course_revenue[c]['collected'] for c in course_revenue],
            'rev_due_data': [course_revenue[c]['due'] for c in course_revenue],
        }
    except Exception as e:
        training_logger.error(f"Error in overview: {e}")
        total_students = total_collected = total_due = total_discount = 0
        fully_paid_count = partially_paid_count = unpaid_count = 0
        total_expenses_val = net_income = placed_students = active_batches = 0
        pending_inquiries = active_employees = total_commissions = total_courses = 0
        collection_rate = 0
        chart_data = {}

    context = {
        'total_students': total_students,
        'total_collected': total_collected,
        'total_due': total_due,
        'total_discount': total_discount,
        'fully_paid_count': fully_paid_count,
        'partially_paid_count': partially_paid_count,
        'unpaid_count': unpaid_count,
        'collection_rate': collection_rate,
        'total_expenses': total_expenses_val,
        'net_income': net_income,
        'placed_students': placed_students,
        'active_batches': active_batches,
        'pending_inquiries': pending_inquiries,
        'active_employees': active_employees,
        'total_commissions': total_commissions,
        'total_courses': total_courses,
        'recent_logs': [],
        'chart_data_json': json.dumps(chart_data),
    }
    return render(request, 'training/overview.html', context)


@login_required
@module_access('training')
def inquiries(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'delete' and doc_id:
            inq = _resolve(doc_id, Inquiry)
            if inq:
                inq.is_active = False
                inq.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_inquiries", doc_id, f"Deleted course inquiry ID {doc_id}")
            messages.success(request, "Inquiry deleted successfully!")
            return redirect('training:inquiries')
        elif action == 'delete_online_reg' and doc_id:
            reg = _resolve(doc_id, Registration)
            if reg:
                reg.is_active = False
                reg.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_registrations", doc_id, f"Deleted online registration ID {doc_id}")
            messages.success(request, "Online registration deleted successfully!")
            return redirect('training:inquiries')
        else:
            inq_count = Inquiry.objects.count()
            inquiry_key = f"INQ-{inq_count + 1:06d}"
            Inquiry.objects.create(
                inquiry_key=inquiry_key,
                name=request.POST.get('name'),
                email=request.POST.get('email'),
                phone=request.POST.get('phone'),
                subject=request.POST.get('subject'),
                message=request.POST.get('message'),
                source=request.POST.get('source', 'Direct'),
                status=request.POST.get('status', 'New'),
            )
            log_training_action(request.user, "CREATE", "trn_inquiries", inquiry_key, f"Logged manual inquiry")
            messages.success(request, "Inquiry saved successfully!")
            return redirect('training:inquiries')

    inquiries_list = _get_collection_data(Inquiry, order_by='-created_at')
    online_regs = _get_collection_data(Registration, order_by='-created_at')
    courses = _get_collection_data(Course)
    return render(request, 'training/inquiries.html', {
        'inquiries': inquiries_list,
        'online_registrations': online_regs,
        'courses': courses,
    })


@login_required
@module_access('training')
def employee_database(request):
    employees = list(Employee.objects.filter(is_active=True).values(
        'pk', 'first_name', 'last_name', 'email', 'phone', 'status',
        'emp_id', 'designation',
    ))
    for e in employees:
        e['id'] = e.pop('pk') or ''
        e['employee_name'] = f"{e.pop('first_name', '')} {e.pop('last_name', '')}".strip()
        e['employee_id'] = e.pop('emp_id')
        if e.get('designation'):
            e['designation'] = e['designation']
        else:
            e['designation'] = ''
    employees_json = json.dumps(employees, default=str)
    return render(request, 'training/employee_database.html', {
        'employees': employees,
        'employees_json': employees_json,
    })


@login_required
@module_access('training')
def trainer_database(request):
    employees = list(Employee.objects.filter(is_active=True).values(
        'first_name', 'last_name', 'email', 'phone', 'designation', 'employee_type', 'emp_id',
    ))
    trainers = []
    for emp in employees:
        desig = (emp.get('designation') or '').lower()
        emp_type = emp.get('employee_type') or ''
        if 'trainer' in desig or 'expert' in desig or emp_type == 'External Professionals' or 'instructor' in desig:
            emp['employee_name'] = f"{emp.pop('first_name', '')} {emp.pop('last_name', '')}".strip()
            emp['employee_id'] = emp.pop('emp_id')
            trainers.append(emp)
    trainers_json = json.dumps(trainers, default=str)
    return render(request, 'training/trainer_database.html', {
        'trainers': trainers,
        'trainers_json': trainers_json,
    })


@login_required
@module_access('training')
def contact_directory(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            inst = _resolve(doc_id, Institute)
            if inst:
                inst.is_active = False
                inst.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_institutes", doc_id, f"Deleted public institute record ID {doc_id}")
            messages.success(request, "Institute contact deleted successfully!")
        else:
            data = {
                'name': request.POST.get('name'),
                'contact_person': request.POST.get('contactPerson'),
                'email': request.POST.get('email'),
                'phone': request.POST.get('phone'),
                'institute_type': request.POST.get('type', 'University'),
                'location': request.POST.get('location'),
                'website': request.POST.get('website'),
                'status': request.POST.get('status', 'Active'),
                'notes': request.POST.get('notes'),
            }
            if doc_id:
                inst = _resolve(doc_id, Institute)
                if inst:
                    for k, v in data.items():
                        setattr(inst, k, v)
                    inst.save()
                log_training_action(request.user, "UPDATE", "trn_institutes", doc_id, f"Updated public training institute: {data['name']}")
            else:
                obj = Institute.objects.create(**data)
                log_training_action(request.user, "CREATE", "trn_institutes", str(obj.pk), f"Registered public training institute: {data['name']}")
            messages.success(request, "Institute contact saved successfully!")
        return redirect('training:contact_directory')

    students = _get_collection_data(Registration, order_by='-created_at')
    institutes = _get_collection_data(Institute, order_by='name')
    courses = _get_collection_data(Course)
    payments = _get_collection_data(Payment)

    for reg in students:
        s_id = reg.get('student_id')
        crs = reg.get('course', '')
        if hasattr(reg, 'course') and reg.get('course'):
            crs_name = reg['course']
        else:
            crs_name = str(crs)
        clean_crs = re.sub(r'[^a-zA-Z0-9]', '', crs_name) if crs_name else ''
        doc_key = f"{s_id}_{clean_crs}" if s_id and clean_crs else None

        pay_record = None
        if doc_key:
            pay_record = next((p for p in payments if p.get('id') == doc_key), None)
        if not pay_record and s_id:
            pay_record = next((p for p in payments if str(p.get('student_id')) == str(s_id)), None)

        pay_status = "Unpaid"
        if pay_record:
            pay_status = pay_record.get('status', 'Unpaid')
            fee = float(pay_record.get('total_fee', 0.0))
            disc = float(pay_record.get('discount', 0.0))
            if fee - disc == 0.0 or reg.get('is_free_batch'):
                pay_status = "Fully Paid"
        reg['paymentStatus'] = pay_status

    students_json = json.dumps(students, default=str)
    institutes_json = json.dumps(institutes, default=str)

    return render(request, 'training/contact_directory.html', {
        'students': students,
        'students_json': students_json,
        'institutes': institutes,
        'institutes_json': institutes_json,
        'courses': courses,
    })


@login_required
@module_access('training')
def brand_ambassadors(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            amb = _resolve(doc_id, Ambassador)
            if amb:
                amb.is_active = False
                amb.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_ambassadors", doc_id, f"Deleted brand ambassador record ID {doc_id}")
            messages.success(request, "Brand ambassador deleted successfully!")
        else:
            data = {
                'name': request.POST.get('name'),
                'email': request.POST.get('email'),
                'phone': request.POST.get('phone'),
                'region': request.POST.get('region'),
                'commission_rate': float(request.POST.get('commissionRate', 0.0)),
                'status': request.POST.get('status', 'Active'),
                'notes': request.POST.get('notes'),
            }
            if doc_id:
                amb = _resolve(doc_id, Ambassador)
                if amb:
                    for k, v in data.items():
                        setattr(amb, k, v)
                    amb.save()
                log_training_action(request.user, "UPDATE", "trn_ambassadors", doc_id, f"Updated brand ambassador: {data['name']}")
            else:
                obj = Ambassador.objects.create(**data)
                log_training_action(request.user, "CREATE", "trn_ambassadors", str(obj.pk), f"Registered brand ambassador: {data['name']}")
            messages.success(request, "Brand ambassador saved successfully!")
        return redirect('training:brand_ambassadors')

    ambassadors = _get_collection_data(Ambassador, order_by='name')
    ambassadors_json = json.dumps(ambassadors, default=str)
    return render(request, 'training/brand_ambassadors.html', {
        'ambassadors': ambassadors,
        'ambassadors_json': ambassadors_json,
    })


@login_required
@module_access('training')
def course_creation(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            course = _resolve(doc_id, Course)
            if course:
                course.is_active = False
                course.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_courses", doc_id, f"Deleted course ID {doc_id}")
            messages.success(request, "Course deleted successfully!")
        else:
            title = request.POST.get('title').strip()
            data = {
                'title': title,
                'code': request.POST.get('code', '').strip().upper(),
                'target': request.POST.get('target', ''),
                'trainer': request.POST.get('trainer', ''),
                'description': request.POST.get('description', ''),
                'duration': request.POST.get('duration', ''),
                'fee': float(request.POST.get('fee', 0.0)),
                'status': request.POST.get('status', 'Active'),
                'icon': request.POST.get('icon', 'bi bi-book'),
            }
            course = Course.objects.filter(title=title).first()
            if course:
                for k, v in data.items():
                    setattr(course, k, v)
                course.save()
            else:
                obj = Course.objects.create(**data)
            log_training_action(request.user, "CREATE", "trn_courses", title, f"Saved training course: {title}")
            messages.success(request, "Course saved successfully!")
        return redirect('training:course_creation')

    courses = _get_collection_data(Course, order_by='title')
    batches = _get_collection_data(Batch, order_by='-created_at')
    employees = Employee.objects.filter(is_active=True)
    trainers = []
    for emp in employees:
        desig = (emp.designation or '').lower()
        if 'trainer' in desig or emp.employee_type == 'External Professionals':
            trainers.append({'id': str(emp.pk), 'name': f"{emp.first_name} {emp.last_name}".strip()})
    return render(request, 'training/course_creation.html', {
        'courses': courses,
        'batches': batches,
        'trainers': trainers,
    })


@login_required
@module_access('training')
def batch_management(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            batch = _resolve(doc_id, Batch)
            if batch:
                batch.is_active = False
                batch.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_batches", doc_id, f"Deleted batch ID {doc_id}")
            messages.success(request, "Batch deleted successfully!")
        else:
            batch_id = request.POST.get('batchId')
            course_id = request.POST.get('courseName')
            data = {
                'batch_id': batch_id,
                'course_id': course_id,
                'schedule': request.POST.get('schedule'),
                'class_days': request.POST.get('classDays'),
                'capacity': int(request.POST.get('capacity', 10)),
                'status': request.POST.get('status', 'Upcoming'),
                'trainer': request.POST.get('trainer', ''),
                'trainer_id': request.POST.get('trainerId', ''),
                'start_date': request.POST.get('startDate'),
                'end_date': request.POST.get('endDate'),
                'total_classes': int(request.POST.get('totalClasses', 12)),
            }
            batch = Batch.objects.filter(batch_id=batch_id).first()
            if batch:
                for k, v in data.items():
                    setattr(batch, k, v)
                batch.save()
            else:
                obj = Batch.objects.create(**data)
            log_training_action(request.user, "CREATE", "trn_batches", batch_id, f"Saved training batch: {batch_id}")
            messages.success(request, "Batch saved successfully!")
        return redirect('training:batch_management')

    batches = _get_collection_data(Batch, order_by='-created_at')
    courses = _get_collection_data(Course)
    registrations = _get_collection_data(Registration)
    employees = Employee.objects.filter(is_active=True)
    trainers = []
    for emp in employees:
        desig = (emp.designation or '').lower()
        if 'trainer' in desig or emp.employee_type == 'External Professionals':
            trainers.append({'id': str(emp.pk), 'name': f"{emp.first_name} {emp.last_name}".strip()})
    return render(request, 'training/batch_management.html', {
        'batches': batches,
        'courses': courses,
        'registrations': registrations,
        'trainers': trainers,
    })


@login_required
@module_access('training')
def class_calendar(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            cls = _resolve(doc_id, ClassSession)
            if cls:
                cls.is_active = False
                cls.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_classes", doc_id, f"Cancelled scheduled class ID {doc_id}")
            messages.success(request, "Scheduled class cancelled successfully!")
        else:
            data = {
                'class_title': request.POST.get('class_title'),
                'course_id': request.POST.get('course_title'),
                'date': request.POST.get('date'),
                'time': request.POST.get('time'),
                'classroom_or_link': request.POST.get('classroom_or_link'),
            }
            obj = ClassSession.objects.create(**data)
            log_training_action(request.user, "CREATE", "trn_classes", str(obj.pk), f"Scheduled class: {data['class_title']}")
            messages.success(request, "Class scheduled successfully!")
        return redirect('training:class_calendar')

    classes = _get_collection_data(ClassSession, order_by='date')
    courses = _get_collection_data(Course)
    batches = _get_collection_data(Batch)
    registrations = _get_collection_data(Registration)

    employees = Employee.objects.filter(is_active=True)
    trainers = []
    for emp in employees:
        desig = (emp.designation or '').lower()
        if 'trainer' in desig or emp.employee_type == 'External Professionals':
            trainers.append({'id': str(emp.pk), 'name': f"{emp.first_name} {emp.last_name}".strip()})

    batches_json = json.dumps(batches, default=str)
    trainers_json = json.dumps(trainers, default=str)
    classes_json = json.dumps(classes, default=str)
    registrations_json = json.dumps(registrations, default=str)

    return render(request, 'training/class_calendar.html', {
        'classes': classes,
        'courses': courses,
        'batches': batches,
        'trainers': trainers,
        'registrations': registrations,
        'batches_json': batches_json,
        'trainers_json': trainers_json,
        'classes_json': classes_json,
        'registrations_json': registrations_json,
    })


@login_required
@module_access('training')
def student_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')

        if action == 'delete' and doc_id:
            reg = _resolve(doc_id, Registration)
            if reg:
                reg.is_active = False
                reg.save(update_fields=['is_active'])
                pay = Payment.objects.filter(registration=reg).first()
                if pay:
                    pay.is_active = False
                    pay.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_registrations", doc_id, f"Removed student enrollment registration: {doc_id}")
            messages.success(request, "Student enrollment deleted successfully!")
            return redirect('training:student_list')

        elif action == 'delete_online_reg' and doc_id:
            reg = _resolve(doc_id, Registration)
            if reg:
                reg.is_active = False
                reg.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_registrations", doc_id, f"Deleted online registration ID {doc_id}")
            messages.success(request, "Online registration deleted successfully!")
            return redirect('training:student_list')

        else:
            fullName = request.POST.get('fullName').strip()
            email = request.POST.get('email').strip()
            phone = request.POST.get('phone').strip()
            course_id = request.POST.get('course')
            batch_id = request.POST.get('batch').strip()
            education = request.POST.get('education')
            schedule = request.POST.get('schedule')
            classDays = request.POST.get('classDays')

            isJobHolder = request.POST.get('isJobHolder') == 'true'
            companyName = request.POST.get('companyName', '').strip() if isJobHolder else ''
            designation = request.POST.get('designation', '').strip() if isJobHolder else ''
            kam = request.POST.get('kam')
            isFreeBatch = request.POST.get('isFreeBatch') == 'true'
            message = request.POST.get('message', '').strip()

            from solutions.views import _get_or_create_person as get_or_create_contact
            contact_id = get_or_create_contact(name=fullName, email=email, phone=phone, role='student')

            batch_obj = _resolve(batch_id, Batch)
            batch_capacity = int(batch_obj.capacity) if batch_obj else 10

            studentId = request.POST.get('studentId', '').strip()
            existing_count = Registration.objects.filter(is_active=True, batch=batch_obj).exclude(pk=doc_id if doc_id else None).count()

            if existing_count >= batch_capacity:
                return HttpResponse(f"Error: Selected batch '{batch_id}' is already full ({existing_count}/{batch_capacity}).", status=400)

            if not doc_id and studentId:
                already = Registration.objects.filter(is_active=True, student_id=studentId, course_id=course_id).exists()
                if already:
                    return HttpResponse(f"Error: Student with ID {studentId} is already enrolled.", status=400)

            course_obj = _resolve(course_id, Course)

            if doc_id:
                reg = _resolve(doc_id, Registration)
                if reg:
                    reg.full_name = fullName
                    reg.email = email
                    reg.phone = phone
                    reg.course = course_obj
                    reg.batch = batch_obj
                    reg.education = education
                    reg.schedule = schedule
                    reg.class_days = classDays
                    reg.message = message
                    reg.is_job_holder = isJobHolder
                    reg.company_name = companyName
                    reg.designation = designation
                    reg.kam = kam
                    reg.is_free_batch = isFreeBatch
                    reg.contact_id = contact_id or ''
                    reg.save()

                    pay = Payment.objects.filter(registration=reg).first()
                    if pay:
                        fee = float(pay.total_fee)
                        disc = float(pay.discount)
                        paid = float(pay.amount_paid)
                        effective = max(0.0, fee - disc)
                        due = max(0.0, effective - paid)
                        pay_status = "Fully Paid" if (effective == 0.0 or isFreeBatch) else ("Partially Paid" if paid > 0 else "Unpaid")
                        pay.student_name = fullName
                        pay.email = email
                        pay.course = course_obj
                        pay.batch = batch_obj
                        pay.due_amount = due
                        pay.status = pay_status
                        pay.save()

                log_training_action(request.user, "UPDATE", "trn_registrations", doc_id, f"Updated student registration: {fullName}")
                messages.success(request, "Student enrollment updated successfully!")

            else:
                if not studentId:
                    all_regs = Registration.objects.filter(is_active=True)
                    studentId = generate_student_id(all_regs)

                if not course_obj:
                    messages.error(request, "Course not found.")
                    return redirect('training:student_list')

                reg = Registration.objects.create(
                    student_id=studentId,
                    full_name=fullName,
                    email=email,
                    phone=phone,
                    course=course_obj,
                    batch=batch_obj,
                    education=education,
                    schedule=schedule,
                    class_days=classDays,
                    message=message,
                    is_job_holder=isJobHolder,
                    company_name=companyName,
                    designation=designation,
                    kam=kam or '',
                    is_free_batch=isFreeBatch,
                    contact_id=contact_id or '',
                )
                totalFee = float(request.POST.get('totalFee', 0.0))
                discount = float(request.POST.get('discount', 0.0))
                amountPaid = float(request.POST.get('amountPaid', 0.0))
                paymentType = request.POST.get('paymentType', 'Cash')
                transactionId = request.POST.get('transactionId', '').strip()
                enableInstallments = request.POST.get('enableInstallments') == 'true'
                registrationFee = amountPaid if enableInstallments else 0.0

                installments = []
                installments_json = request.POST.get('installments')
                if installments_json:
                    try:
                        installments = json.loads(installments_json)
                    except Exception:
                        pass

                effective = max(0.0, totalFee - discount)
                due = max(0.0, effective - amountPaid)
                pay_status = "Fully Paid" if (effective == 0.0 or isFreeBatch) else ("Fully Paid" if amountPaid >= effective else ("Partially Paid" if amountPaid > 0 else "Unpaid"))

                pay = Payment.objects.create(
                    registration=reg,
                    student_id=studentId,
                    student_name=fullName,
                    email=email,
                    course=course_obj,
                    course_name=course_obj.title if course_obj else '',
                    batch=batch_obj.batch_id if batch_obj else '',
                    total_fee=totalFee,
                    discount=discount,
                    amount_paid=amountPaid,
                    due_amount=due,
                    status=pay_status,
                    payment_type=paymentType,
                    transaction_id=transactionId if paymentType != 'Cash' else '',
                    registration_fee=registrationFee,
                    installments=installments,
                )
                log_training_action(request.user, "CREATE", "trn_registrations", reg.student_id, f"Registered student {fullName}")
                messages.success(request, "Student enrollment saved successfully!")

                online_key = request.POST.get('onlineKey')
                if online_key:
                    if online_key.startswith('INQ-'):
                        inq = _resolve(online_key, Inquiry)
                        if inq:
                            inq.status = 'Converted'
                            inq.save(update_fields=['status'])
                        log_training_action(request.user, "UPDATE", "trn_inquiries", online_key, f"Converted inquiry {online_key} to registered student")
                    else:
                        old_reg = _resolve(online_key, Registration)
                        if old_reg:
                            old_reg.is_active = False
                            old_reg.save(update_fields=['is_active'])
                        log_training_action(request.user, "DELETE", "trn_registrations", online_key, f"Deleted processed online registration key: {online_key}")

            return redirect('training:student_list')

    students = _get_collection_data(Registration, order_by='-created_at')
    courses = _get_collection_data(Course)
    batches = _get_collection_data(Batch)
    ambassadors_db = _get_collection_data(Ambassador)
    employees = Employee.objects.filter(is_active=True)

    bd_employees = []
    for emp in employees:
        desig = (emp.designation or '').lower()
        if 'business development' in desig or 'bd' in desig:
            bd_employees.append({
                'employee_id': emp.emp_id,
                'employee_name': f"{emp.first_name} {emp.last_name}".strip(),
            })
    kams = []
    for a in ambassadors_db:
        kams.append({'id': a.get('id'), 'name': a.get('name', '') + ' (Brand Ambassador)'})
    for e in bd_employees:
        kams.append({'id': e['employee_id'], 'name': e['employee_name'] + ' (BD Executive)'})

    online_regs = [s for s in students if not s.get('course')]
    manual_students = [s for s in students if s.get('course')]

    students_json = json.dumps(manual_students, default=str)
    online_regs_json = json.dumps(online_regs, default=str)
    return render(request, 'training/student_list.html', {
        'students': manual_students,
        'students_json': students_json,
        'online_regs_json': online_regs_json,
        'courses': courses,
        'batches': batches,
        'kams': kams,
    })


@login_required
@module_access('training')
def installment_plan(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'update_payment' and doc_id:
            pay = _resolve(doc_id, Payment)
            if not pay:
                messages.error(request, "Payment record not found.")
                return redirect('training:installment_plan')

            total_fee = float(pay.total_fee)
            discount = float(request.POST.get('discount', pay.discount))
            amount_paid = float(request.POST.get('amount_paid', pay.amount_paid))
            payment_type = request.POST.get('payment_type', pay.payment_type)
            transaction_id = request.POST.get('transaction_id', pay.transaction_id or '')

            installments = []
            installments_json = request.POST.get('installments')
            if installments_json:
                try:
                    installments = json.loads(installments_json)
                except Exception:
                    pass
            else:
                installments = pay.installments

            effective_fee = max(0.0, total_fee - discount)
            due = max(0.0, effective_fee - amount_paid)

            reg = pay.registration
            is_free = reg.is_free_batch if reg else False

            pay_status = "Unpaid"
            if effective_fee == 0.0 or is_free:
                pay_status = "Fully Paid"
            elif amount_paid > 0:
                pay_status = "Fully Paid" if amount_paid >= effective_fee else "Partially Paid"

            old_paid = float(pay.amount_paid)
            collected_diff = amount_paid - old_paid
            if collected_diff > 0:
                try:
                    cash_account = ChartOfAccount.objects.filter(account_code='11100').first()
                    ar_account = ChartOfAccount.objects.filter(account_code='11200').first()
                    if cash_account and ar_account:
                        je_count = JournalEntry.objects.count()
                        entry_id = f"JV-{je_count + 1:04d}"
                        je = JournalEntry.objects.create(
                            entry_code=entry_id,
                            posting_date=str(date.today()),
                            reference_document=f"Receipt: Student Installment {doc_id}",
                            narration=f"Automated posting for student installment payment: Student ID {pay.student_id} ({pay.student_name})",
                            status='Posted',
                            created_by_name=request.user.username or 'system',
                            approved_by_name=request.user.username or 'system',
                        )
                        JournalEntryLine.objects.create(journal_entry=je, account=cash_account, debit_amount=collected_diff, credit_amount=0.0)
                        JournalEntryLine.objects.create(journal_entry=je, account=ar_account, debit_amount=0.0, credit_amount=collected_diff)
                        log_training_action(request.user, "CREATE", "fin_journal_entries", entry_id, f"Posted automated journal entry {entry_id}")
                except Exception as ge_err:
                    training_logger.error(f"Error posting automatic journal entry for payment: {ge_err}")

            pay.discount = discount
            pay.amount_paid = amount_paid
            pay.due_amount = due
            pay.status = pay_status
            pay.payment_type = payment_type
            pay.transaction_id = transaction_id if payment_type != 'Cash' else ''
            pay.installments = installments
            pay.save()

            log_training_action(request.user, "UPDATE", "payments", doc_id, f"Updated installment payment details for student record {doc_id}")
            messages.success(request, "Payment plan updated successfully!")

            if due <= 0.0 and reg:
                assess = Assessment.objects.filter(registration=reg, status='Passed').first()
                if assess:
                    cert_exists = Certificate.objects.filter(registration=reg).exists()
                    if not cert_exists:
                        cert_id = f"CERT-{pay.student_id}"
                        Certificate.objects.create(
                            certificate_id=cert_id,
                            registration=reg,
                            student_id=pay.student_id or '',
                            student_name=pay.student_name or '',
                            course_name=pay.course_name or '',
                            issue_date=date.today(),
                            grade=assess.grade or 'Passed',
                            status='Issued',
                        )
                        log_training_action(request.user, "CREATE", "trn_certificates", cert_id, f"Auto-issued certificate {cert_id}")

        return redirect('training:installment_plan')

    payments = Payment.objects.filter(is_active=True).order_by('-created_at')
    installment_plans = [p for p in payments if len(p.installments or []) > 0]
    return render(request, 'training/installment_plan.html', {'payments': installment_plans})


@login_required
@module_access('training')
def revenue_tracker(request):
    payments = Payment.objects.filter(is_active=True, amount_paid__gt=0).order_by('-created_at')
    return render(request, 'training/revenue_tracker.html', {'payments': payments})


@login_required
@module_access('training')
def expense_tracker(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            exp = _resolve(doc_id, Expense)
            if exp:
                exp.is_active = False
                exp.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_expenses", doc_id, f"Removed training expense ID {doc_id}")
            messages.success(request, "Training expense removed successfully!")
        else:
            data = {
                'category': request.POST.get('category'),
                'sub_category': request.POST.get('subCategory', ''),
                'description': request.POST.get('description', ''),
                'amount': float(request.POST.get('amount', 0.0)),
                'date': request.POST.get('date'),
                'payment_method': request.POST.get('paymentMethod', 'Cash'),
            }
            if doc_id:
                exp = _resolve(doc_id, Expense)
                if exp:
                    for k, v in data.items():
                        setattr(exp, k, v)
                    exp.save()
                log_training_action(request.user, "UPDATE", "trn_expenses", doc_id, f"Updated expense")
            else:
                obj = Expense.objects.create(**data)
                log_training_action(request.user, "CREATE", "trn_expenses", str(obj.pk), f"Logged expense of {data['amount']} under category {data['category']}")
            messages.success(request, "Training expense logged successfully!")
        return redirect('training:expense_tracker')

    expenses = _get_collection_data(Expense, order_by='-date')
    return render(request, 'training/expense_tracker.html', {'expenses': expenses})


@login_required
@module_access('training')
def sales_management(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            comm = _resolve(doc_id, Commission)
            if comm:
                comm.is_active = False
                comm.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_commissions", doc_id, f"Deleted sales commission payout ID {doc_id}")
            messages.success(request, "Sales commission payout deleted successfully!")
        else:
            comm_count = Commission.objects.count()
            comm_id = f"COMM-{comm_count + 1:04d}"
            data = {
                'agent_id': request.POST.get('agentId'),
                'agent_name': request.POST.get('agentName'),
                'month': request.POST.get('month'),
                'year': request.POST.get('year'),
                'referral_count': int(request.POST.get('referralCount', 0)),
                'payout_amount': float(request.POST.get('payoutAmount', 0.0)),
                'status': request.POST.get('status', 'Unpaid'),
                'notes': request.POST.get('notes'),
            }
            Commission.objects.create(**data)
            log_training_action(request.user, "CREATE", "trn_commissions", comm_id, f"Created sales commission payout")
            messages.success(request, "Sales commission payout saved successfully!")
        return redirect('training:sales_management')

    commissions = _get_collection_data(Commission, order_by='-created_at')
    ambassadors = _get_collection_data(Ambassador)
    employees = Employee.objects.filter(is_active=True)

    bd_employees = []
    for emp in employees:
        desig = (emp.designation or '').lower()
        if 'business development' in desig or 'bd' in desig:
            bd_employees.append({
                'employee_id': emp.emp_id,
                'employee_name': f"{emp.first_name} {emp.last_name}".strip(),
            })

    agents = []
    for a in ambassadors:
        agents.append({
            'id': a.get('id'),
            'name': a.get('name', '') + ' (Brand Ambassador)',
            'rate': float(a.get('commission_rate', 0.0)),
            'isAmbassador': True,
        })
    for e in bd_employees:
        agents.append({
            'id': e['employee_id'],
            'name': e['employee_name'] + ' (BD Executive)',
            'rate': 0.0,
            'isAmbassador': False,
        })

    registrations = _get_collection_data(Registration)
    payments = _get_collection_data(Payment)

    return render(request, 'training/sales_management.html', {
        'commissions': commissions,
        'agents': agents,
        'registrations': registrations,
        'payments': payments,
    })


@login_required
@module_access('training')
def course_assessments(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            assess = _resolve(doc_id, Assessment)
            if assess:
                assess.is_active = False
                assess.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_assessments", doc_id, f"Deleted assessment record ID {doc_id}")
            messages.success(request, "Course assessment deleted successfully!")
        else:
            studentId = request.POST.get('studentId').strip()
            courseName = request.POST.get('courseName')
            clean_course = re.sub(r'[^a-zA-Z0-9]', '', courseName)
            assess_id = f"{studentId}_{clean_course}"

            reg = Registration.objects.filter(student_id=studentId, course__title=courseName).first()
            batch_obj = Batch.objects.filter(batch_id=request.POST.get('batchId').strip()).first()

            data = {
                'registration': reg,
                'student_id': studentId,
                'student_name': request.POST.get('studentName').strip(),
                'course_name': courseName,
                'batch': batch_obj,
                'theory_marks': float(request.POST.get('theoryMarks', 0.0)),
                'practical_marks': float(request.POST.get('practicalMarks', 0.0)),
                'total_marks': float(request.POST.get('totalMarks', 0.0)),
                'grade': request.POST.get('grade').strip(),
                'status': request.POST.get('status', 'Passed'),
                'remarks': request.POST.get('remarks', ''),
            }

            assess = Assessment.objects.filter(registration=reg).first()
            if assess:
                for k, v in data.items():
                    setattr(assess, k, v)
                assess.save()
            else:
                obj = Assessment.objects.create(**data)
            log_training_action(request.user, "CREATE", "trn_assessments", assess_id, f"Saved marks/grades assessment for student")
            messages.success(request, "Course assessment saved successfully!")

            if data['status'] == 'Passed' and reg:
                pay = Payment.objects.filter(registration=reg).first()
                if pay and float(pay.due_amount) <= 0.0:
                    cert_exists = Certificate.objects.filter(registration=reg).exists()
                    if not cert_exists:
                        cert_id = f"CERT-{studentId}"
                        Certificate.objects.create(
                            certificate_id=cert_id,
                            registration=reg,
                            student_id=studentId,
                            student_name=data['student_name'],
                            course_name=courseName,
                            issue_date=date.today(),
                            grade=data['grade'],
                            status='Issued',
                        )
                        log_training_action(request.user, "CREATE", "trn_certificates", cert_id, f"Auto-issued certificate {cert_id}")

        return redirect('training:course_assessments')

    assessments = _get_collection_data(Assessment, order_by='-created_at')
    students = _get_collection_data(Registration)
    courses = _get_collection_data(Course)
    return render(request, 'training/course_assessments.html', {
        'assessments': assessments,
        'students': students,
        'courses': courses,
    })


@login_required
@module_access('training')
def certificates(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            cert = _resolve(doc_id, Certificate)
            if cert:
                cert.is_active = False
                cert.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_certificates", doc_id, f"Deleted issued certificate ID {doc_id}")
            messages.success(request, "Certificate deleted successfully!")
        else:
            cert_id = request.POST.get('certificateId').strip()
            reg = Registration.objects.filter(student_id=request.POST.get('studentId').strip()).first()
            data = {
                'certificate_id': cert_id,
                'registration': reg,
                'student_id': request.POST.get('studentId').strip(),
                'student_name': request.POST.get('studentName').strip(),
                'course_name': request.POST.get('courseName'),
                'issue_date': request.POST.get('issueDate'),
                'grade': request.POST.get('grade', '').strip(),
                'status': request.POST.get('status', 'Issued'),
                'batch': request.POST.get('batch', '').strip(),
            }
            cert = Certificate.objects.filter(certificate_id=cert_id).first()
            if cert:
                for k, v in data.items():
                    setattr(cert, k, v)
                cert.save()
            else:
                obj = Certificate.objects.create(**data)
            log_training_action(request.user, "CREATE", "trn_certificates", cert_id, f"Issued verification certificate")
            messages.success(request, "Verification certificate issued successfully!")
        return redirect('training:certificates')

    certificates_list = _get_collection_data(Certificate, order_by='-issue_date')
    students = _get_collection_data(Registration)
    payments = _get_collection_data(Payment)
    assessments = _get_collection_data(Assessment)
    courses = _get_collection_data(Course)

    eligibility_map = {}
    for r in students:
        s_id = r.get('student_id')
        crs = r.get('course_name') or r.get('course', '')
        if s_id and crs:
            clean_crs = re.sub(r'[^a-zA-Z0-9]', '', str(crs))
            doc_key = f"{s_id}_{clean_crs}"

            pay_record = next((p for p in payments if p.get('student_id') == s_id and p.get('course_name') == str(crs)), None)
            pay_status = "Unpaid"
            if pay_record:
                pay_status = pay_record.get('status', 'Unpaid')
                fee = float(pay_record.get('total_fee', 0.0))
                disc = float(pay_record.get('discount', 0.0))
                if fee - disc == 0.0 or r.get('is_free_batch'):
                    pay_status = "Fully Paid"

            assess_record = next((a for a in assessments if a.get('student_id') == s_id and a.get('course_name') == str(crs)), None)
            assess_status = "Not Started"
            grade = ""
            if assess_record:
                assess_status = assess_record.get('status', 'Not Started')
                grade = assess_record.get('grade', '')

            is_eligible = (pay_status == 'Fully Paid') and (assess_status in ['Passed', 'passed', 'Pass'])
            eligibility_map[doc_key] = {
                'paymentStatus': pay_status,
                'assessmentStatus': assess_status,
                'grade': grade,
                'eligible': is_eligible,
            }

    return render(request, 'training/certificates.html', {
        'certificates': certificates_list,
        'students': students,
        'courses': courses,
        'eligibility_json': json.dumps(eligibility_map),
    })


@login_required
@module_access('training')
def job_placement(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            jp = _resolve(doc_id, JobPlacement)
            if jp:
                jp.is_active = False
                jp.save(update_fields=['is_active'])
            log_training_action(request.user, "DELETE", "trn_job_placements", doc_id, f"Deleted job placement record ID {doc_id}")
            messages.success(request, "Job placement deleted successfully!")
        else:
            reg = Registration.objects.filter(student_id=request.POST.get('studentId').strip()).first()
            data = {
                'registration': reg,
                'student_id': request.POST.get('studentId').strip(),
                'student_name': request.POST.get('studentName').strip(),
                'course_name': request.POST.get('courseName'),
                'batch': Batch.objects.filter(batch_id=request.POST.get('batchId', '').strip()).first(),
                'company': request.POST.get('company').strip(),
                'job_title': request.POST.get('jobTitle').strip(),
                'placement_date': request.POST.get('placementDate'),
                'salary': float(request.POST.get('salary', 0.0)),
                'placement_type': request.POST.get('placementType', 'Full-time'),
                'notes': request.POST.get('notes'),
            }
            if doc_id:
                jp = _resolve(doc_id, JobPlacement)
                if jp:
                    for k, v in data.items():
                        setattr(jp, k, v)
                    jp.save()
                log_training_action(request.user, "UPDATE", "trn_job_placements", doc_id, f"Updated job placement")
            else:
                obj = JobPlacement.objects.create(**data)
                log_training_action(request.user, "CREATE", "trn_job_placements", str(obj.pk), f"Recorded job placement")
            messages.success(request, "Job placement recorded successfully!")
        return redirect('training:job_placement')

    placements = _get_collection_data(JobPlacement, order_by='-placement_date')
    students = _get_collection_data(Registration)
    return render(request, 'training/job_placement.html', {
        'placements': placements,
        'students': students,
    })


@login_required
@module_access('training')
def reports(request):
    courses = _get_collection_data(Course)
    students = _get_collection_data(Registration)
    revenue = _get_collection_data(Payment)
    expenses = _get_collection_data(Expense)
    placements = _get_collection_data(JobPlacement)

    total_revenue = sum(float(r.get('amount_paid', 0)) for r in revenue)
    total_expenses_val = sum(float(e.get('amount', 0)) for e in expenses)
    net_income = total_revenue - total_expenses_val

    report_summary = {
        'total_courses': len(courses),
        'total_students': len(students),
        'total_revenue': total_revenue,
        'total_expenses': total_expenses_val,
        'net_income': net_income,
        'placed_count': len(placements),
    }

    course_perf = {}
    for c in courses:
        title = c.get('title')
        course_perf[title] = {'enrolled': 0, 'collected': 0.0, 'due': 0.0}
    for s in students:
        crs = s.get('course_name') or s.get('course') or ''
        if crs in course_perf:
            course_perf[crs]['enrolled'] += 1
    for p in revenue:
        crs = p.get('course_name') or ''
        if crs in course_perf:
            course_perf[crs]['collected'] += float(p.get('amount_paid', 0))
            course_perf[crs]['due'] += float(p.get('due_amount', 0))

    course_list = []
    for k, v in course_perf.items():
        course_list.append({
            'title': k,
            'enrolled': v['enrolled'],
            'collected': v['collected'],
            'due': v['due'],
        })

    return render(request, 'training/reports.html', {
        'report_summary': report_summary,
        'course_perf': course_list,
    })
