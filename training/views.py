from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from config.firebase import db
from google.cloud import firestore
from django.contrib.auth.decorators import login_required
from accounts.decorators import module_access
from config.logger import training_logger
import random
import re
import json
from datetime import datetime

# Helper to get Firestore collection data ordered by createdAt descending
def get_collection_data(collection_name, default_data=None):
    if default_data is None:
        default_data = []
    try:
        docs = db.collection(collection_name).order_by('createdAt', direction=firestore.Query.DESCENDING).stream()
        results = []
        for doc in docs:
            item = doc.to_dict()
            item['id'] = doc.id
            results.append(item)
        if not results:
            return default_data
        return results
    except Exception as e:
        # Fallback to order-less stream in case createdAt is missing/not-indexed
        try:
            docs = db.collection(collection_name).stream()
            results = []
            for doc in docs:
                item = doc.to_dict()
                item['id'] = doc.id
                results.append(item)
            if not results:
                return default_data
            return results
        except Exception as e2:
            training_logger.error(f"Error fetching {collection_name}: {e2}")
            return default_data

# Internal helper to generate student ID matching 495XXX sequence
def generate_student_id(course_name, batch_name, registrations_list):
    max_serial = 0
    for r in registrations_list:
        student_id = r.get('studentId')
        if student_id:
            match = re.search(r'(?:^|-)(495\d{3})$', student_id)
            if match:
                num = int(match.group(1)[3:])
                if num > max_serial:
                    max_serial = num
    next_serial = max_serial + 1
    serial_str = f"{next_serial:03d}"
    return f"495{serial_str}"

# Helper to generate sequence IDs like EXP-0001, INST-0001, AMB-0001, PLACE-0001, LOG-00001
def get_next_seq_id(collection_name, prefix, id_field, padding_size=4):
    try:
        docs = db.collection(collection_name).stream()
        max_num = 0
        for doc in docs:
            data = doc.to_dict()
            val = data.get(id_field)
            if val and val.startswith(prefix):
                num_part = val[len(prefix):]
                try:
                    num = int(num_part)
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass
        next_num = max_num + 1
        return f"{prefix}{next_num:0{padding_size}d}"
    except Exception as e:
        training_logger.error(f"Error generating next sequence ID for {collection_name}: {e}")
        return f"{prefix}{'1'.zfill(padding_size)}"

# Audit logging helper
def log_training_action(user, action_type, collection_name, record_id, details):
    try:
        log_id = get_next_seq_id('sys_audit_logs', 'LOG-', 'log_id', 5)
        user_email = getattr(user, 'email', '') or getattr(user, 'username', '') or str(user)
        local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.collection('sys_audit_logs').document(log_id).set({
            'log_id': log_id,
            'user_email': user_email,
            'action_type': action_type,
            'collection_name': collection_name,
            'record_id': record_id,
            'details': details,
            'local_time': local_time,
            'createdAt': firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        training_logger.error(f"Error logging action: {e}")

@module_access('training')
def index(request):
    return redirect('training:overview')

@module_access('training')
def overview(request):
    try:
        registrations = get_collection_data('trn_registrations')
        payments = get_collection_data('trn_payments')
        expenses = get_collection_data('trn_expenses')
        placements = get_collection_data('trn_job_placements')
        batches = get_collection_data('trn_batches')
        inquiries = get_collection_data('trn_inquiries')
        online_regs = get_collection_data('trn_registrations')
        employees = get_collection_data('hrm_employees')
        commissions = get_collection_data('trn_commissions')
        courses = get_collection_data('trn_courses')
        
        # Calculate stats
        total_students = len({r.get('studentId') for r in registrations if r.get('studentId')})
        total_collected = sum(float(p.get('amountPaid', 0)) for p in payments)
        total_due = sum(float(p.get('dueAmount', 0)) for p in payments)
        total_discount = sum(float(p.get('discount', 0)) for p in payments)
        
        fully_paid_count = sum(1 for p in payments if p.get('status') == 'Fully Paid')
        partially_paid_count = sum(1 for p in payments if p.get('status') == 'Partially Paid')
        unpaid_count = sum(1 for p in payments if p.get('status') == 'Unpaid')
        
        total_expenses = sum(float(e.get('amount', 0)) for e in expenses)
        net_income = total_collected - total_expenses
        placed_students = len(placements)
        active_batches = sum(1 for b in batches if b.get('status') == 'Active')
        pending_inquiries = sum(1 for i in inquiries if i.get('status') == 'New')
        pending_online_reg = len(online_regs)
        active_employees = sum(1 for emp in employees if emp.get('status', 'Active') == 'Active')
        total_commissions = sum(float(c.get('payoutAmount', 0)) for c in commissions)
        total_courses = len(courses)
        
        collection_rate = (total_collected / (total_collected + total_due) * 100) if (total_collected + total_due) > 0 else 0
        
        # Fetch audit logs (recent 10)
        logs = get_collection_data('sys_audit_logs')[:10]
        
        # Chart data formatting
        # 1. Course Enrollment Count
        course_counts = {}
        for r in registrations:
            c = r.get('course')
            if c:
                course_counts[c] = course_counts.get(c, 0) + 1
        
        # 2. Monthly cash flow
        monthly_collections = {}
        for p in payments:
            try:
                ca = p.get('createdAt')
                if ca:
                    if hasattr(ca, 'year'):
                        dt = ca
                    else:
                        dt = datetime.strptime(str(ca)[:19], '%Y-%m-%d %H:%M:%S')
                    ym = dt.strftime('%Y-%m')
                    monthly_collections[ym] = monthly_collections.get(ym, 0.0) + float(p.get('amountPaid', 0))
            except Exception:
                pass
        
        monthly_expenses = {}
        for e in expenses:
            try:
                dt_str = e.get('date')
                if dt_str:
                    ym = dt_str[:7] # YYYY-MM
                    monthly_expenses[ym] = monthly_expenses.get(ym, 0.0) + float(e.get('amount', 0))
            except Exception:
                pass
                
        all_months = sorted(list(set(monthly_collections.keys()) | set(monthly_expenses.keys())))
        
        # 3. Revenue by Course
        course_revenue = {}
        for c in course_counts.keys():
            course_revenue[c] = {'collected': 0.0, 'due': 0.0}
        for p in payments:
            c = p.get('courseName')
            if c:
                if c not in course_revenue:
                    course_revenue[c] = {'collected': 0.0, 'due': 0.0}
                course_revenue[c]['collected'] += float(p.get('amountPaid', 0))
                course_revenue[c]['due'] += float(p.get('dueAmount', 0))
                
        # Prep chart JSON
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
        total_expenses = net_income = placed_students = active_batches = 0
        pending_inquiries = pending_online_reg = active_employees = total_commissions = total_courses = 0
        collection_rate = 0
        logs = []
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
        'total_expenses': total_expenses,
        'net_income': net_income,
        'placed_students': placed_students,
        'active_batches': active_batches,
        'pending_inquiries': pending_inquiries,
        'pending_online_reg': pending_online_reg,
        'active_employees': active_employees,
        'total_commissions': total_commissions,
        'total_courses': total_courses,
        'recent_logs': logs,
        'chart_data_json': json.dumps(chart_data),
    }
    return render(request, 'training/overview.html', context)

@module_access('training')
def inquiries(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        from django.http import HttpResponseRedirect
        if action == 'delete' and doc_id:
            db.collection('trn_inquiries').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_inquiries", doc_id, f"Deleted course inquiry ID {doc_id}")
            messages.success(request, "Inquiry deleted successfully!")
            return HttpResponseRedirect(reverse('training:inquiries') + '?tab=directory')
        elif action == 'delete_online_reg' and doc_id:
            db.collection('trn_registrations').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_registrations", doc_id, f"Deleted online registration ID {doc_id}")
            messages.success(request, "Online registration deleted successfully!")
            return HttpResponseRedirect(reverse('training:inquiries') + '?tab=pending')
        else:
            inquiry_key = get_next_seq_id('trn_inquiries', 'INQ-', 'inquiryKey', 6)
            data = {
                'inquiryKey': inquiry_key,
                'name': request.POST.get('name'),
                'email': request.POST.get('email'),
                'phone': request.POST.get('phone'),
                'subject': request.POST.get('subject'),
                'message': request.POST.get('message'),
                'source': request.POST.get('source', 'Direct'),
                'status': request.POST.get('status', 'New'),
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            db.collection('trn_inquiries').document(inquiry_key).set(data)
            log_training_action(request.user, "CREATE", "trn_inquiries", inquiry_key, f"Logged manual inquiry: {data['name']} - {data['subject']}")
            messages.success(request, "Inquiry saved successfully!")
            return HttpResponseRedirect(reverse('training:inquiries') + '?tab=directory')

    inquiries_list = get_collection_data('trn_inquiries')
    online_regs = get_collection_data('trn_registrations')
    courses = get_collection_data('trn_courses')
    return render(request, 'training/inquiries.html', {
        'inquiries': inquiries_list, 
        'online_registrations': online_regs,
        'courses': courses
    })

@module_access('training')
def employee_database(request):
    # Read-only central employee listing
    employees = get_collection_data('hrm_employees')
    employees_json = json.dumps(employees, default=str)
    return render(request, 'training/employee_database.html', {
        'employees': employees,
        'employees_json': employees_json
    })

@module_access('training')
def trainer_database(request):
    # Filter trainers from central employee registry
    employees = get_collection_data('hrm_employees')
    trainers = []
    for emp in employees:
        desig = emp.get('designation', '').lower()
        emp_type = emp.get('employee_type', '')
        if 'trainer' in desig or 'expert' in desig or emp_type == 'External Professionals' or 'instructor' in desig:
            trainers.append(emp)
    trainers_json = json.dumps(trainers, default=str)
    return render(request, 'training/trainer_database.html', {
        'trainers': trainers,
        'trainers_json': trainers_json
    })

@module_access('training')
def contact_directory(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            db.collection('trn_institutes').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_institutes", doc_id, f"Deleted public institute record ID {doc_id}")
            messages.success(request, "Institute contact deleted successfully!")
        else:
            is_new = not doc_id
            if is_new:
                doc_id = get_next_seq_id('trn_institutes', 'INST-', 'id', 4)
            
            data = {
                'id': doc_id,
                'name': request.POST.get('name'),
                'contactPerson': request.POST.get('contactPerson'),
                'email': request.POST.get('email'),
                'phone': request.POST.get('phone'),
                'type': request.POST.get('type', 'University'),
                'location': request.POST.get('location'),
                'website': request.POST.get('website'),
                'status': request.POST.get('status', 'Active'),
                'notes': request.POST.get('notes'),
            }
            if is_new:
                data['createdAt'] = firestore.SERVER_TIMESTAMP
            
            db.collection('trn_institutes').document(doc_id).set(data, merge=True)
            log_training_action(
                request.user, 
                "CREATE" if is_new else "UPDATE", 
                "trn_institutes", 
                doc_id, 
                f"{'Registered' if is_new else 'Updated'} public training institute: {data['name']}"
            )
            messages.success(request, "Institute contact saved successfully!")
        return redirect('training:contact_directory')

    students = get_collection_data('trn_registrations')
    institutes = get_collection_data('trn_institutes')
    courses = get_collection_data('trn_courses')
    payments = get_collection_data('trn_payments')

    # Resolve payment status for each student registration
    for reg in students:
        s_id = reg.get('studentId')
        crs = reg.get('course', '')
        clean_crs = re.sub(r'[^a-zA-Z0-9]', '', crs) if crs else ''
        doc_key = f"{s_id}_{clean_crs}" if s_id and clean_crs else None
        
        pay_record = None
        if doc_key:
            pay_record = next((p for p in payments if p.get('id') == doc_key), None)
        if not pay_record and s_id:
            pay_record = next((p for p in payments if p.get('studentId') == s_id), None)
            
        pay_status = "Unpaid"
        if pay_record:
            pay_status = pay_record.get('status', 'Unpaid')
            fee = float(pay_record.get('totalFee', 0.0))
            disc = float(pay_record.get('discount', 0.0))
            if fee - disc == 0.0 or reg.get('isFreeBatch'):
                pay_status = "Fully Paid"
        reg['paymentStatus'] = pay_status

    students_json = json.dumps(students, default=str)
    institutes_json = json.dumps(institutes, default=str)

    return render(request, 'training/contact_directory.html', {
        'students': students,
        'students_json': students_json,
        'institutes': institutes,
        'institutes_json': institutes_json,
        'courses': courses
    })

@module_access('training')
def brand_ambassadors(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            db.collection('trn_ambassadors').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_ambassadors", doc_id, f"Deleted brand ambassador record ID {doc_id}")
            messages.success(request, "Brand ambassador deleted successfully!")
        else:
            is_new = not doc_id
            if is_new:
                doc_id = get_next_seq_id('trn_ambassadors', 'AMB-', 'id', 4)
            
            comm_rate_str = request.POST.get('commissionRate')
            try:
                commission_rate = float(comm_rate_str) if comm_rate_str else 0.0
            except ValueError:
                commission_rate = 0.0

            data = {
                'id': doc_id,
                'name': request.POST.get('name'),
                'email': request.POST.get('email'),
                'phone': request.POST.get('phone'),
                'region': request.POST.get('region'),
                'commissionRate': commission_rate,
                'status': request.POST.get('status', 'Active'),
                'notes': request.POST.get('notes'),
            }
            if is_new:
                data['createdAt'] = firestore.SERVER_TIMESTAMP
            
            db.collection('trn_ambassadors').document(doc_id).set(data, merge=True)
            log_training_action(
                request.user, 
                "CREATE" if is_new else "UPDATE", 
                "trn_ambassadors", 
                doc_id, 
                f"{'Registered' if is_new else 'Updated'} brand ambassador: {data['name']}"
            )
            messages.success(request, "Brand ambassador saved successfully!")
        return redirect('training:brand_ambassadors')

    ambassadors = get_collection_data('trn_ambassadors')
    ambassadors_json = json.dumps(ambassadors, default=str)
    return render(request, 'training/brand_ambassadors.html', {
        'ambassadors': ambassadors,
        'ambassadors_json': ambassadors_json
    })

@module_access('training')
def course_creation(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            db.collection('trn_courses').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_courses", doc_id, f"Deleted course ID {doc_id}")
            messages.success(request, "Course deleted successfully!")
        else:
            title = request.POST.get('title')
            clean_title = title.strip()
            data = {
                'id': request.POST.get('code', '').strip().upper(),
                'title': clean_title,
                'code': request.POST.get('code', '').strip().upper(),
                'target': request.POST.get('target', ''),
                'trainer': request.POST.get('trainer', ''),
                'description': request.POST.get('description', ''),
                'duration': request.POST.get('duration', ''),
                'fee': float(request.POST.get('fee', 0.0)),
                'status': request.POST.get('status', 'Active'),
                'icon': request.POST.get('icon', 'bi bi-book'),
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            db.collection('trn_courses').document(clean_title).set(data, merge=True)
            log_training_action(request.user, "CREATE", "trn_courses", clean_title, f"Saved training course: {clean_title}")
            messages.success(request, "Course saved successfully!")
        return redirect('training:course_creation')

    courses = get_collection_data('trn_courses')
    batches = get_collection_data('trn_batches')
    employees = get_collection_data('hrm_employees')
    trainers = [emp for emp in employees if 'trainer' in emp.get('designation', '').lower() or emp.get('employee_type') == 'External Professionals']
    return render(request, 'training/course_creation.html', {
        'courses': courses,
        'batches': batches,
        'trainers': trainers
    })

@module_access('training')
def batch_management(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            db.collection('trn_batches').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_batches", doc_id, f"Deleted batch ID {doc_id}")
            messages.success(request, "Batch deleted successfully!")
        else:
            batch_id = request.POST.get('batchId')
            data = {
                'batchId': batch_id,
                'courseName': request.POST.get('courseName'),
                'schedule': request.POST.get('schedule'),
                'classDays': request.POST.get('classDays'),
                'capacity': int(request.POST.get('capacity', 10)),
                'status': request.POST.get('status', 'Upcoming'),
                'trainer': request.POST.get('trainer', ''),
                'trainerId': request.POST.get('trainerId', ''),
                'startDate': request.POST.get('startDate'),
                'endDate': request.POST.get('endDate'),
                'totalClasses': int(request.POST.get('totalClasses', 12)),
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            db.collection('trn_batches').document(batch_id).set(data, merge=True)
            log_training_action(request.user, "CREATE", "trn_batches", batch_id, f"Saved training batch: {batch_id} for course {data['courseName']}")
            messages.success(request, "Batch saved successfully!")
        return redirect('training:batch_management')

    batches = get_collection_data('trn_batches')
    courses = get_collection_data('trn_courses')
    registrations = get_collection_data('trn_registrations')
    employees = get_collection_data('hrm_employees')
    trainers = [emp for emp in employees if 'trainer' in emp.get('designation', '').lower() or emp.get('employee_type') == 'External Professionals']
    return render(request, 'training/batch_management.html', {
        'batches': batches, 
        'courses': courses,
        'registrations': registrations,
        'trainers': trainers
    })

@module_access('training')
def class_calendar(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            db.collection('trn_classes').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_classes", doc_id, f"Cancelled scheduled class ID {doc_id}")
            messages.success(request, "Scheduled class cancelled successfully!")
        else:
            data = {
                'class_title': request.POST.get('class_title'),
                'course_title': request.POST.get('course_title'),
                'date': request.POST.get('date'),
                'time': request.POST.get('time'),
                'classroom_or_link': request.POST.get('classroom_or_link'),
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            db.collection('trn_classes').add(data)
            log_training_action(request.user, "CREATE", "trn_classes", "new_class", f"Scheduled class: {data['class_title']}")
            messages.success(request, "Class scheduled successfully!")
        return redirect('training:class_calendar')

    classes = get_collection_data('trn_classes')
    courses = get_collection_data('trn_courses')
    batches = get_collection_data('trn_batches')
    employees = get_collection_data('hrm_employees')
    registrations = get_collection_data('trn_registrations')

    trainers = [emp for emp in employees if 'trainer' in emp.get('designation', '').lower() or emp.get('employee_type') == 'External Professionals']

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

@module_access('training')
def student_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        
        if action == 'delete' and doc_id:
            # Delete registration and corresponding payment record
            db.collection('trn_registrations').document(doc_id).delete()
            db.collection('trn_payments').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_registrations", doc_id, f"Removed student enrollment registration: {doc_id}")
            messages.success(request, "Student enrollment deleted successfully!")
            return redirect('training:student_list')
            
        elif action == 'delete_online_reg' and doc_id:
            db.collection('trn_registrations').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_registrations", doc_id, f"Deleted online registration ID {doc_id}")
            messages.success(request, "Online registration deleted successfully!")
            return redirect('training:student_list')
            
        else:
            # Add or Update
            fullName = request.POST.get('fullName').strip()
            email = request.POST.get('email').strip()
            phone = request.POST.get('phone').strip()
            course = request.POST.get('course')
            batch = request.POST.get('batch').strip()
            education = request.POST.get('education')
            schedule = request.POST.get('schedule')
            classDays = request.POST.get('classDays')
            
            isJobHolder = request.POST.get('isJobHolder') == 'true'
            companyName = request.POST.get('companyName', '').strip() if isJobHolder else ''
            designation = request.POST.get('designation', '').strip() if isJobHolder else ''
            kam = request.POST.get('kam')
            isFreeBatch = request.POST.get('isFreeBatch') == 'true'
            message = request.POST.get('message', '').strip()
            
            from config.contacts_helper import get_or_create_contact
            contact_id = get_or_create_contact(name=fullName, email=email, phone=phone, role='student')

            # Validation: Batch Capacity (Max 10)
            batch_snap = db.collection('trn_batches').document(batch).get()
            batch_capacity = 10
            if batch_snap.exists:
                batch_capacity = int(batch_snap.to_dict().get('capacity', 10))
            
            # Find current registrations in batch
            studentId = request.POST.get('studentId', '').strip()
            existing_count = 0
            all_regs = get_collection_data('trn_registrations')
            for r in all_regs:
                if r.get('batch') == batch and r.get('id') != doc_id:
                     existing_count += 1
            
            if existing_count >= batch_capacity:
                # Return error
                return HttpResponse(f"Error: Selected batch '{batch}' is already full ({existing_count}/{batch_capacity}).", status=400)
            
            # If creating new, check if already enrolled in this course
            if not doc_id and studentId:
                already_enrolled = any(r.get('studentId') == studentId and r.get('course') == course for r in all_regs)
                if already_enrolled:
                    return HttpResponse(f"Error: Student with ID {studentId} is already enrolled in course '{course}'.", status=400)

            if doc_id:
                # Update
                reg_ref = db.collection('trn_registrations').document(doc_id)
                reg_ref.update({
                    'fullName': fullName,
                    'email': email,
                    'phone': phone,
                    'course': course,
                    'batch': batch,
                    'education': education,
                    'schedule': schedule,
                    'classDays': classDays,
                    'message': message,
                    'isJobHolder': isJobHolder,
                    'companyName': companyName,
                    'designation': designation,
                    'kam': kam,
                    'isFreeBatch': isFreeBatch,
                    'contact_id': contact_id
                })
                
                # Sync payment details
                pay_ref = db.collection('trn_payments').document(doc_id)
                pay_snap = pay_ref.get()
                if pay_snap.exists:
                    pay_data = pay_snap.to_dict()
                    fee = float(pay_data.get('totalFee', 0.0))
                    disc = float(pay_data.get('discount', 0.0))
                    paid = float(pay_data.get('amountPaid', 0.0))
                    effective = max(0.0, fee - disc)
                    due = max(0.0, effective - paid)
                    status = "Fully Paid" if (effective == 0.0 or isFreeBatch) else ("Partially Paid" if paid > 0 else "Unpaid")
                    
                    pay_ref.update({
                        'studentName': fullName,
                        'email': email,
                        'courseName': course,
                        'batch': batch,
                        'dueAmount': due,
                        'status': status,
                        'updatedAt': firestore.SERVER_TIMESTAMP
                    })
                
                log_training_action(request.user, "UPDATE", "trn_registrations", doc_id, f"Updated student registration: {fullName}")
                messages.success(request, "Student enrollment updated successfully!")
                
            else:
                # Create
                if not studentId:
                    studentId = generate_student_id(course, batch, all_regs)
                
                clean_course = re.sub(r'[^a-zA-Z0-9]', '', course)
                generated_doc_id = f"{studentId}_{clean_course}"
                
                # Write registration
                db.collection('trn_registrations').document(generated_doc_id).set({
                    'studentId': studentId,
                    'fullName': fullName,
                    'email': email,
                    'phone': phone,
                    'course': course,
                    'batch': batch,
                    'education': education,
                    'schedule': schedule,
                    'classDays': classDays,
                    'message': message,
                    'isJobHolder': isJobHolder,
                    'companyName': companyName,
                    'designation': designation,
                    'kam': kam,
                    'isFreeBatch': isFreeBatch,
                    'contact_id': contact_id,
                    'createdAt': firestore.SERVER_TIMESTAMP
                })
                
                # Financial values
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
                status = "Fully Paid" if (effective == 0.0 or isFreeBatch) else ("Fully Paid" if amountPaid >= effective else ("Partially Paid" if amountPaid > 0 else "Unpaid"))
                
                # Write payment record
                db.collection('trn_payments').document(generated_doc_id).set({
                    'studentId': studentId,
                    'studentName': fullName,
                    'email': email,
                    'courseName': course,
                    'batch': batch,
                    'totalFee': totalFee,
                    'discount': discount,
                    'amountPaid': amountPaid,
                    'dueAmount': due,
                    'status': status,
                    'paymentType': paymentType,
                    'transactionId': transactionId if paymentType != 'Cash' else '',
                    'createdAt': firestore.SERVER_TIMESTAMP,
                    'updatedAt': firestore.SERVER_TIMESTAMP,
                    'registrationFee': registrationFee,
                    'installments': installments
                })
                
                log_training_action(request.user, "CREATE", "trn_registrations", generated_doc_id, f"Registered student {fullName} in course {course} batch {batch}")
                messages.success(request, "Student enrollment saved successfully!")
                
                # If online registration or inquiry conversion
                online_key = request.POST.get('onlineKey')
                if online_key:
                    if online_key.startswith('INQ-'):
                        db.collection('trn_inquiries').document(online_key).update({'status': 'Converted'})
                        log_training_action(request.user, "UPDATE", "trn_inquiries", online_key, f"Converted inquiry {online_key} to registered student")
                    else:
                        db.collection('trn_registrations').document(online_key).delete()
                        log_training_action(request.user, "DELETE", "trn_registrations", online_key, f"Deleted processed online registration key: {online_key}")
            
            return redirect('training:student_list')

    students = get_collection_data('trn_registrations')
    courses = get_collection_data('trn_courses')
    batches = get_collection_data('trn_batches')
    ambassadors = get_collection_data('trn_ambassadors')
    employees = get_collection_data('hrm_employees')
    online_regs = get_collection_data('trn_registrations')
    bd_employees = [emp for emp in employees if emp.get('status') == 'Active' and ('business development' in emp.get('designation', '').lower() or 'bd' in emp.get('designation', '').lower())]
    
    # Combined KAM directory list
    kams = []
    for a in ambassadors:
        kams.append({'id': a['id'], 'name': a['name'] + ' (Brand Ambassador)'})
    for e in bd_employees:
        kams.append({'id': e['employee_id'], 'name': e['employee_name'] + ' (BD Executive)'})
        
    students_json = json.dumps(students, default=str)
    online_regs_json = json.dumps(online_regs, default=str)
    return render(request, 'training/student_list.html', {
        'students': students, 
        'students_json': students_json,
        'online_regs_json': online_regs_json,
        'courses': courses, 
        'batches': batches,
        'kams': kams
    })

@module_access('training')
def installment_plan(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'update_payment' and doc_id:
            pay_ref = db.collection('trn_payments').document(doc_id)
            pay_snap = pay_ref.get()
            if pay_snap.exists:
                pay_data = pay_snap.to_dict()
                total_fee = float(pay_data.get('totalFee', 0))
                discount = float(request.POST.get('discount', pay_data.get('discount', 0)))
                amount_paid = float(request.POST.get('amount_paid', pay_data.get('amountPaid', 0)))
                payment_type = request.POST.get('payment_type', pay_data.get('paymentType', 'Cash'))
                transaction_id = request.POST.get('transaction_id', pay_data.get('transactionId', ''))
                
                installments_json = request.POST.get('installments')
                installments = []
                if installments_json:
                    try:
                        installments = json.loads(installments_json)
                    except Exception:
                        pass
                else:
                    installments = pay_data.get('installments', [])
                
                effective_fee = max(0.0, total_fee - discount)
                due = max(0.0, effective_fee - amount_paid)
                
                # Check registration isFreeBatch status
                reg_snap = db.collection('trn_registrations').document(doc_id).get()
                is_free = False
                if reg_snap.exists:
                    is_free = reg_snap.to_dict().get('isFreeBatch', False)
                
                status = "Unpaid"
                if effective_fee == 0.0 or is_free:
                    status = "Fully Paid"
                elif amount_paid > 0:
                    status = "Fully Paid" if amount_paid >= effective_fee else "Partially Paid"
                
                # Automated GL Journal Posting for new collections
                old_paid = float(pay_data.get('amountPaid', 0.0))
                collected_diff = amount_paid - old_paid
                if collected_diff > 0:
                    try:
                        coa_cash = list(db.collection('fin_chart_of_accounts').where('account_code', '==', '11100').stream())
                        coa_ar = list(db.collection('fin_chart_of_accounts').where('account_code', '==', '11200').stream())
                        cash_id = coa_cash[0].id if coa_cash else '11100_fallback'
                        ar_id = coa_ar[0].id if coa_ar else '11200_fallback'
                        
                        entry_id = get_next_seq_id('fin_journal_entries', 'JV-', 'entry_code', 4)
                        journal_data = {
                            'entry_code': entry_id,
                            'posting_date': datetime.now().strftime('%Y-%m-%d'),
                            'reference_document': f"Receipt: Student Installment {doc_id}",
                            'narration': f"Automated posting for student installment payment: Student ID {pay_data.get('studentId')} ({pay_data.get('studentName')})",
                            'status': 'Posted',
                            'created_by': request.user.username if request.user else 'system',
                            'approved_by': request.user.username if request.user else 'system',
                            'lines': [
                                {'account_id': cash_id, 'debit_amount': collected_diff, 'credit_amount': 0.0},
                                {'account_id': ar_id, 'debit_amount': 0.0, 'credit_amount': collected_diff}
                            ],
                            'created_at': firestore.SERVER_TIMESTAMP
                        }
                        db.collection('fin_journal_entries').document(entry_id).set(journal_data)
                        log_training_action(request.user, "CREATE", "fin_journal_entries", entry_id, f"Posted automated journal entry {entry_id} for collected payment {collected_diff}")
                    except Exception as ge_err:
                        training_logger.error(f"Error posting automatic journal entry for payment: {ge_err}")
                
                pay_ref.update({
                    'discount': discount,
                    'amountPaid': amount_paid,
                    'dueAmount': due,
                    'status': status,
                    'paymentType': payment_type,
                    'transactionId': transaction_id if payment_type != 'Cash' else '',
                    'installments': installments,
                    'updatedAt': firestore.SERVER_TIMESTAMP
                })
                
                log_training_action(request.user, "UPDATE", "payments", doc_id, f"Updated installment payment details for student record {doc_id}")
                messages.success(request, "Payment plan updated successfully!")
                
                # Check for certificate trigger: due is 0 and student passed assessment
                if due <= 0.0:
                    try:
                        clean_course = re.sub(r'[^a-zA-Z0-9]', '', pay_data.get('courseName', ''))
                        assess_id = f"{pay_data.get('studentId')}_{clean_course}"
                        assess_snap = db.collection('trn_assessments').document(assess_id).get()
                        if assess_snap.exists:
                            assess_data = assess_snap.to_dict() or {}
                            if assess_data.get('status') == 'Passed':
                                cert_id = f"CERT-{pay_data.get('studentId')}"
                                cert_snap = db.collection('trn_certificates').document(cert_id).get()
                                if not cert_snap.exists:
                                    cert_data = {
                                        'certificateId': cert_id,
                                        'studentId': pay_data.get('studentId'),
                                        'studentName': pay_data.get('studentName'),
                                        'courseName': pay_data.get('courseName'),
                                        'issueDate': datetime.now().strftime('%Y-%m-%d'),
                                        'grade': assess_data.get('grade', 'Passed'),
                                        'status': 'Issued',
                                        'createdAt': firestore.SERVER_TIMESTAMP
                                    }
                                    db.collection('trn_certificates').document(cert_id).set(cert_data, merge=True)
                                    log_training_action(request.user, "CREATE", "trn_certificates", cert_id, f"Auto-issued certificate {cert_id} upon balance clearance")
                    except Exception as cert_err:
                        training_logger.error(f"Error auto-issuing certificate on payment update: {cert_err}")
                        
        return redirect('training:installment_plan')
        
    payments = get_collection_data('trn_payments')
    installment_plans = [p for p in payments if len(p.get('installments', [])) > 0]
    return render(request, 'training/installment_plan.html', {'payments': installment_plans})

@module_access('training')
def revenue_tracker(request):
    payments = get_collection_data('trn_payments')
    collected_payments = [p for p in payments if float(p.get('amountPaid', 0.0)) > 0.0]
    return render(request, 'training/revenue_tracker.html', {'payments': collected_payments})

@module_access('training')
def expense_tracker(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            db.collection('trn_expenses').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_expenses", doc_id, f"Removed training expense ID {doc_id}")
            messages.success(request, "Training expense removed successfully!")
        else:
            is_new = not doc_id
            if is_new:
                doc_id = get_next_seq_id('trn_expenses', 'EXP-', 'id', 4)
            data = {
                'id': doc_id,
                'category': request.POST.get('category'),
                'subCategory': request.POST.get('subCategory', ''),
                'description': request.POST.get('description', ''),
                'amount': float(request.POST.get('amount', 0.0)),
                'date': request.POST.get('date'),
                'paymentMethod': request.POST.get('paymentMethod', 'Cash'),
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            db.collection('trn_expenses').document(doc_id).set(data, merge=True)
            log_training_action(request.user, "CREATE" if is_new else "UPDATE", "trn_expenses", doc_id, f"Logged expense of {data['amount']} under category {data['category']}")
            messages.success(request, "Training expense logged successfully!")
        return redirect('training:expense_tracker')

    expenses = get_collection_data('trn_expenses')
    return render(request, 'training/expense_tracker.html', {'expenses': expenses})

@module_access('training')
def sales_management(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            db.collection('trn_commissions').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_commissions", doc_id, f"Deleted sales commission payout ID {doc_id}")
            messages.success(request, "Sales commission payout deleted successfully!")
        else:
            comm_id = get_next_seq_id('trn_commissions', 'COMM-', 'id', 4)
            data = {
                'id': comm_id,
                'agentId': request.POST.get('agentId'),
                'agentName': request.POST.get('agentName'),
                'month': request.POST.get('month'),
                'year': request.POST.get('year'),
                'referralCount': int(request.POST.get('referralCount', 0)),
                'payoutAmount': float(request.POST.get('payoutAmount', 0.0)),
                'status': request.POST.get('status', 'Unpaid'),
                'notes': request.POST.get('notes'),
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            db.collection('trn_commissions').document(comm_id).set(data)
            log_training_action(request.user, "CREATE", "trn_commissions", comm_id, f"Created sales commission payout of {data['payoutAmount']} for {data['agentName']}")
            messages.success(request, "Sales commission payout saved successfully!")
        return redirect('training:sales_management')

    commissions = get_collection_data('trn_commissions')
    ambassadors = get_collection_data('trn_ambassadors')
    employees = get_collection_data('hrm_employees')
    bd_employees = [emp for emp in employees if emp.get('status') == 'Active' and ('business development' in emp.get('designation', '').lower() or 'bd' in emp.get('designation', '').lower())]
    
    # Combine agents/kams list
    agents = []
    for a in ambassadors:
        agents.append({'id': a['id'], 'name': a['name'] + ' (Brand Ambassador)', 'rate': a.get('commissionRate', 0.0), 'isAmbassador': True})
    for e in bd_employees:
        agents.append({'id': e['employee_id'], 'name': e['employee_name'] + ' (BD Executive)', 'rate': 0.0, 'isAmbassador': False})

    # Group registrations by agent to count referrals
    registrations = get_collection_data('trn_registrations')
    payments = get_collection_data('trn_payments')

    return render(request, 'training/sales_management.html', {
        'commissions': commissions,
        'agents': agents,
        'registrations': registrations,
        'payments': payments
    })

@module_access('training')
def course_assessments(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            db.collection('trn_assessments').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_assessments", doc_id, f"Deleted assessment record ID {doc_id}")
            messages.success(request, "Course assessment deleted successfully!")
        else:
            studentId = request.POST.get('studentId').strip()
            courseName = request.POST.get('courseName')
            clean_course = re.sub(r'[^a-zA-Z0-9]', '', courseName)
            assess_id = f"{studentId}_{clean_course}"
            
            data = {
                'studentId': studentId,
                'studentName': request.POST.get('studentName').strip(),
                'courseName': courseName,
                'batchId': request.POST.get('batchId').strip(),
                'theoryMarks': float(request.POST.get('theoryMarks', 0.0)),
                'practicalMarks': float(request.POST.get('practicalMarks', 0.0)),
                'totalMarks': float(request.POST.get('totalMarks', 0.0)),
                'grade': request.POST.get('grade').strip(),
                'status': request.POST.get('status', 'Passed'),
                'remarks': request.POST.get('remarks', ''),
                'updatedAt': firestore.SERVER_TIMESTAMP
            }
            db.collection('trn_assessments').document(assess_id).set(data, merge=True)
            log_training_action(request.user, "CREATE", "trn_assessments", assess_id, f"Saved marks/grades assessment for student {data['studentName']} in course {courseName}")
            messages.success(request, "Course assessment saved successfully!")
            
            # Check certificate trigger: student passed and outstanding balance is zero
            if data['status'] == 'Passed':
                try:
                    pay_id = f"{studentId}_{clean_course}"
                    pay_snap = db.collection('trn_payments').document(pay_id).get()
                    if pay_snap.exists:
                        pay_data = pay_snap.to_dict() or {}
                        due = float(pay_data.get('dueAmount', 0.0))
                        if due <= 0.0:
                            cert_id = f"CERT-{studentId}"
                            cert_snap = db.collection('trn_certificates').document(cert_id).get()
                            if not cert_snap.exists:
                                cert_data = {
                                    'certificateId': cert_id,
                                    'studentId': studentId,
                                    'studentName': data['studentName'],
                                    'courseName': courseName,
                                    'issueDate': datetime.now().strftime('%Y-%m-%d'),
                                    'grade': data['grade'],
                                    'status': 'Issued',
                                    'createdAt': firestore.SERVER_TIMESTAMP
                                }
                                db.collection('trn_certificates').document(cert_id).set(cert_data, merge=True)
                                log_training_action(request.user, "CREATE", "trn_certificates", cert_id, f"Auto-issued certificate {cert_id} upon assessment pass")
                except Exception as cert_err:
                    training_logger.error(f"Error auto-issuing certificate on assessment update: {cert_err}")
                    
        return redirect('training:course_assessments')

    assessments = get_collection_data('trn_assessments')
    students = get_collection_data('trn_registrations')
    courses = get_collection_data('trn_courses')
    return render(request, 'training/course_assessments.html', {
        'assessments': assessments,
        'students': students,
        'courses': courses
    })

@module_access('training')
def certificates(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            db.collection('trn_certificates').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_certificates", doc_id, f"Deleted issued certificate ID {doc_id}")
            messages.success(request, "Certificate deleted successfully!")
        else:
            cert_id = request.POST.get('certificateId').strip()
            data = {
                'certificateId': cert_id,
                'studentId': request.POST.get('studentId').strip(),
                'studentName': request.POST.get('studentName').strip(),
                'courseName': request.POST.get('courseName'),
                'issueDate': request.POST.get('issueDate'),
                'grade': request.POST.get('grade', '').strip(),
                'status': request.POST.get('status', 'Issued'),
                'batch': request.POST.get('batch', '').strip(),
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            db.collection('trn_certificates').document(cert_id).set(data)
            log_training_action(request.user, "CREATE", "trn_certificates", cert_id, f"Issued verification certificate to {data['studentName']} for course {data['courseName']}")
            messages.success(request, "Verification certificate issued successfully!")
        return redirect('training:certificates')

    certificates_list = get_collection_data('trn_certificates')
    students = get_collection_data('trn_registrations')
    payments = get_collection_data('trn_payments')
    assessments = get_collection_data('trn_assessments')
    courses = get_collection_data('trn_courses')
    
    # Calculate eligibility contexts to pass to template for search
    eligibility_map = {}
    for r in students:
        s_id = r.get('studentId')
        crs = r.get('course')
        if s_id and crs:
            clean_crs = re.sub(r'[^a-zA-Z0-9]', '', crs)
            doc_key = f"{s_id}_{clean_crs}"
            
            # Check payment status
            pay_record = next((p for p in payments if p.get('id') == doc_key), None)
            pay_status = "Unpaid"
            if pay_record:
                pay_status = pay_record.get('status', 'Unpaid')
                fee = float(pay_record.get('totalFee', 0.0))
                disc = float(pay_record.get('discount', 0.0))
                if fee - disc == 0.0 or r.get('isFreeBatch'):
                    pay_status = "Fully Paid"
                    
            # Check assessment status
            assess_record = next((a for a in assessments if a.get('id') == doc_key), None)
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
                'eligible': is_eligible
            }
            
    return render(request, 'training/certificates.html', {
        'certificates': certificates_list,
        'students': students,
        'courses': courses,
        'eligibility_json': json.dumps(eligibility_map)
    })

@module_access('training')
def job_placement(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        doc_id = request.POST.get('doc_id')
        if action == 'delete' and doc_id:
            db.collection('trn_job_placements').document(doc_id).delete()
            log_training_action(request.user, "DELETE", "trn_job_placements", doc_id, f"Deleted job placement record ID {doc_id}")
            messages.success(request, "Job placement deleted successfully!")
        else:
            is_new = not doc_id
            if is_new:
                doc_id = get_next_seq_id('trn_job_placements', 'PLACE-', 'id', 4)
            data = {
                'id': doc_id,
                'studentId': request.POST.get('studentId').strip(),
                'studentName': request.POST.get('studentName').strip(),
                'courseName': request.POST.get('courseName'),
                'batchId': request.POST.get('batchId', '').strip(),
                'company': request.POST.get('company').strip(),
                'jobTitle': request.POST.get('jobTitle').strip(),
                'placementDate': request.POST.get('placementDate'),
                'salary': float(request.POST.get('salary', 0.0)),
                'placementType': request.POST.get('placementType', 'Full-time'),
                'notes': request.POST.get('notes'),
                'createdAt': firestore.SERVER_TIMESTAMP
            }
            db.collection('trn_job_placements').document(doc_id).set(data, merge=True)
            log_training_action(request.user, "CREATE" if is_new else "UPDATE", "trn_job_placements", doc_id, f"Recorded job placement for graduate {data['studentName']} at {data['company']}")
            messages.success(request, "Job placement recorded successfully!")
        return redirect('training:job_placement')

    placements = get_collection_data('trn_job_placements')
    students = get_collection_data('trn_registrations')
    return render(request, 'training/job_placement.html', {
        'placements': placements,
        'students': students
    })

@module_access('training')
def reports(request):
    courses = get_collection_data('trn_courses')
    students = get_collection_data('trn_registrations')
    revenue = get_collection_data('trn_payments')
    expenses = get_collection_data('trn_expenses')
    placements = get_collection_data('trn_job_placements')
    
    total_revenue = sum(float(r.get('amountPaid', 0)) for r in revenue)
    total_expenses = sum(float(e.get('amount', 0)) for e in expenses)
    net_income = total_revenue - total_expenses
    
    report_summary = {
        'total_courses': len(courses),
        'total_students': len(students),
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_income': net_income,
        'placed_count': len(placements)
    }
    
    # Calculate performance metrics by course
    course_perf = {}
    for c in courses:
        title = c.get('title')
        course_perf[title] = {'enrolled': 0, 'collected': 0.0, 'due': 0.0}
    for s in students:
        crs = s.get('course')
        if crs in course_perf:
            course_perf[crs]['enrolled'] += 1
    for p in revenue:
        crs = p.get('courseName')
        if crs in course_perf:
            course_perf[crs]['collected'] += float(p.get('amountPaid', 0))
            course_perf[crs]['due'] += float(p.get('dueAmount', 0))
            
    course_list = []
    for k, v in course_perf.items():
        course_list.append({
            'title': k,
            'enrolled': v['enrolled'],
            'collected': v['collected'],
            'due': v['due']
        })

    return render(request, 'training/reports.html', {
        'report_summary': report_summary,
        'course_perf': course_list
    })


