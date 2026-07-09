from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from config.firebase import db
from google.cloud import firestore
from accounts.decorators import employee_portal_access
from config.logger import hrm_logger
from config.services.integration_service import IntegrationService
import random
from datetime import datetime, date
from django.db.models import Q


def _get_collection(collection_name, order_field='createdAt', descending=True):
    try:
        direction = firestore.Query.DESCENDING if descending else firestore.Query.ASCENDING
        docs = db.collection(collection_name).order_by(order_field, direction=direction).stream()
        results = []
        for doc in docs:
            item = doc.to_dict()
            item['id'] = doc.id
            results.append(item)
        return results
    except Exception as e:
        hrm_logger.error(f"Error fetching {collection_name}: {e}")
        return []


@employee_portal_access
def dashboard(request, employee_data):
    if not employee_data:
        return redirect('portal_login')

    try:
        emp_name = employee_data.get('name', '')

        # Attendance this month
        today = date.today()
        month_prefix = today.strftime('%Y-%m')
        att_docs = db.collection('hrm_attendance').where('name', '==', emp_name).stream()
        present_count = 0
        absent_count = 0
        late_count = 0
        for doc in att_docs:
            d = doc.to_dict()
            if d.get('date', '').startswith(month_prefix):
                status = d.get('status', '')
                if status == 'Present':
                    present_count += 1
                elif status == 'Absent':
                    absent_count += 1
                elif status == 'Late':
                    late_count += 1

        # Pending leave requests
        pending_leaves = sum(1 for lv in db.collection('hrm_leaves')
                             .where('name', '==', emp_name)
                             .where('status', '==', 'Pending').stream())

        # Performance reviews
        total_reviews = sum(1 for rv in db.collection('hrm_performance_reviews')
                            .where('employee', '==', emp_name).stream())

        # Recent leaves
        leave_docs = db.collection('hrm_leaves') \
            .where('name', '==', emp_name) \
            .order_by('createdAt', direction=firestore.Query.DESCENDING) \
            .limit(5).stream()
        recent_leaves = []
        for doc in leave_docs:
            d = doc.to_dict()
            d['id'] = doc.id
            recent_leaves.append(d)

        # Upcoming holidays
        holiday_docs = db.collection('hrm_holidays').stream()
        today_str = today.isoformat()
        upcoming_holidays = []
        for doc in holiday_docs:
            d = doc.to_dict()
            if d.get('from_date', '') >= today_str:
                d['id'] = doc.id
                upcoming_holidays.append(d)
        upcoming_holidays = sorted(upcoming_holidays, key=lambda h: h.get('from_date', ''))[:5]

        # Leave balance
        from hrm.models import Employee as SQLEmployee, LeaveBalance
        emp_obj = SQLEmployee.objects.filter(email=employee_data.get('email', '')).first()
        balances = LeaveBalance.objects.filter(employee=emp_obj, is_active=True) if emp_obj else []

    except Exception as e:
        hrm_logger.error(f"Portal dashboard error: {e}")
        present_count = absent_count = late_count = pending_leaves = total_reviews = 0
        recent_leaves = upcoming_holidays = balances = []

    context = {
        'employee': employee_data,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'pending_leaves': pending_leaves,
        'total_reviews': total_reviews,
        'recent_leaves': recent_leaves,
        'upcoming_holidays': upcoming_holidays,
        'balances': balances,
    }
    return render(request, 'portal/dashboard.html', context)


@employee_portal_access
def profile(request, employee_data):
    if not employee_data:
        return redirect('portal_login')

    if request.method == 'POST':
        try:
            doc_id = employee_data.get('id')
            updates = {}
            fields = ['phone', 'alt_phone', 'city', 'zip',
                      'ec_primary_name', 'ec_primary_relation', 'ec_primary_mobile',
                      'ec_secondary_name', 'ec_secondary_relation', 'ec_secondary_mobile']
            for f in fields:
                val = request.POST.get(f, '').strip()
                if val:
                    updates[f] = val
            if updates:
                db.collection('hrm_employees').document(doc_id).update(updates)
                messages.success(request, "Profile updated successfully.")
                # Re-fetch to show updated data
                doc = db.collection('hrm_employees').document(doc_id).get()
                if doc.exists:
                    employee_data = doc.to_dict()
                    employee_data['id'] = doc.id
        except Exception as e:
            hrm_logger.error(f"Portal profile update error: {e}")
            messages.error(request, "Failed to update profile.")
        return redirect('portal:profile')

    context = {'employee': employee_data}
    return render(request, 'portal/profile.html', context)


@employee_portal_access
def attendance(request, employee_data):
    if not employee_data:
        return redirect('portal_login')

    emp_name = employee_data.get('name', '')
    logs = _get_collection('hrm_attendance')
    my_logs = [l for l in logs if l.get('name') == emp_name]

    context = {
        'employee': employee_data,
        'logs': my_logs,
    }
    return render(request, 'portal/attendance.html', context)


@employee_portal_access
def leave(request, employee_data):
    if not employee_data:
        return redirect('portal_login')

    emp_name = employee_data.get('name', '')
    emp_email = employee_data.get('email', '')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'apply_leave':
            try:
                from_date = request.POST.get('from_date', '')
                to_date = request.POST.get('to_date', '')
                leave_type = request.POST.get('leave_type', '')
                reason = request.POST.get('reason', '')

                try:
                    fd = date.fromisoformat(from_date)
                    td = date.fromisoformat(to_date)
                    days = (td - fd).days + 1
                    duration = f"{days} Day{'s' if days != 1 else ''}"
                except Exception:
                    duration = ''

                # Check leave balance
                from hrm.models import Employee as SQLEmployee, LeaveBalance
                emp_obj = SQLEmployee.objects.filter(email=emp_email).first()
                if emp_obj:
                    balance = LeaveBalance.objects.filter(
                        employee=emp_obj, leave_type=leave_type, is_active=True
                    ).first()
                    if balance and balance.available <= 0:
                        messages.error(request, f"Insufficient {leave_type} leave balance.")
                        return redirect('portal:leave')

                _, new_ref = db.collection('hrm_leaves').add({
                    'name': emp_name,
                    'type': leave_type,
                    'from_date': from_date,
                    'to_date': to_date,
                    'duration': duration,
                    'reason': reason,
                    'status': 'Pending',
                    'createdAt': firestore.SERVER_TIMESTAMP,
                })
                messages.success(request, "Leave request submitted successfully.")
            except Exception as e:
                hrm_logger.error(f"Portal leave apply error: {e}")
                messages.error(request, "Failed to submit leave request.")

        elif action == 'cancel_leave':
            doc_id = request.POST.get('doc_id')
            if doc_id:
                try:
                    doc = db.collection('hrm_leaves').document(doc_id).get()
                    if doc.exists and doc.to_dict().get('name') == emp_name and doc.to_dict().get('status') == 'Pending':
                        db.collection('hrm_leaves').document(doc_id).delete()
                        messages.success(request, "Leave request cancelled.")
                except Exception as e:
                    hrm_logger.error(f"Portal leave cancel error: {e}")

        return redirect('portal:leave')

    my_leaves = _get_collection('hrm_leaves')
    my_leaves = [l for l in my_leaves if l.get('name') == emp_name]

    holidays = _get_collection('hrm_holidays')

    # Get leave balances from Django ORM
    from hrm.models import Employee as SQLEmployee, LeaveBalance
    emp_obj = SQLEmployee.objects.filter(email=emp_email).first()
    balances = []
    if emp_obj:
        balances = LeaveBalance.objects.filter(employee=emp_obj, is_active=True)

    context = {
        'employee': employee_data,
        'leaves': my_leaves,
        'holidays': holidays,
        'balances': balances,
    }
    return render(request, 'portal/leave.html', context)


@employee_portal_access
def payslips(request, employee_data):
    if not employee_data:
        return redirect('portal_login')

    emp_name = employee_data.get('name', '')
    payrolls = _get_collection('hrm_payrolls')

    context = {
        'employee': employee_data,
        'payrolls': payrolls,
    }
    return render(request, 'portal/payslips.html', context)


@employee_portal_access
def performance(request, employee_data):
    if not employee_data:
        return redirect('portal_login')

    emp_name = employee_data.get('name', '')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'submit_self_assessment':
            try:
                doc_id = request.POST.get('doc_id')
                strengths = request.POST.get('strengths', '')
                improvements = request.POST.get('improvements', '')
                goals = request.POST.get('goals', '')
                if doc_id:
                    db.collection('hrm_performance_reviews').document(doc_id).update({
                        'strengths': strengths,
                        'improvements': improvements,
                        'goals': goals,
                        'status': 'Manager-Review',
                    })
                    messages.success(request, "Self-assessment submitted successfully.")
            except Exception as e:
                hrm_logger.error(f"Portal self-assessment error: {e}")
                messages.error(request, "Failed to submit self-assessment.")
        return redirect('portal:performance')

    reviews = _get_collection('hrm_performance_reviews')
    my_reviews = [r for r in reviews if r.get('employee') == emp_name]

    pips_data = _get_collection('hrm_pips')
    my_pips = [p for p in pips_data if p.get('employee') == emp_name]

    context = {
        'employee': employee_data,
        'reviews': my_reviews,
        'pips': my_pips,
    }
    return render(request, 'portal/performance.html', context)


@employee_portal_access
def documents(request, employee_data):
    if not employee_data:
        return redirect('portal_login')

    emp_name = employee_data.get('name', '')

    all_docs = _get_collection('hrm_documents')
    my_docs = [d for d in all_docs if d.get('employee') == emp_name]

    all_assets = _get_collection('hrm_assets')
    my_assets = [a for a in all_assets if a.get('employee') == emp_name]

    context = {
        'employee': employee_data,
        'documents': my_docs,
        'assets': my_assets,
    }
    return render(request, 'portal/documents.html', context)


@employee_portal_access
def training_catalog(request, employee_data):
    if not employee_data:
        return redirect('portal_login')

    courses = _get_collection('trn_courses')
    batches = _get_collection('trn_batches')
    emp_name = employee_data.get('name', '')
    emp_email = employee_data.get('email', '')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'express_interest':
            try:
                course_id = request.POST.get('course_id')
                course_doc = db.collection('trn_courses').document(course_id).get()
                course_name = course_doc.to_dict().get('title', '') if course_doc.exists else ''
                db.collection('hrm_training_interests').add({
                    'employee': emp_name,
                    'employee_email': emp_email,
                    'course_name': course_name,
                    'course_id': course_id,
                    'status': 'Interested',
                    'createdAt': firestore.SERVER_TIMESTAMP,
                })
                messages.success(request, f"Interest registered for {course_name}.")
            except Exception as e:
                hrm_logger.error(f"Training interest error: {e}")
                messages.error(request, "Failed to register interest.")
        return redirect('portal:training_catalog')

    my_nominations = _get_collection('hrm_training_interests')
    my_nominations = [n for n in my_nominations if n.get('employee') == emp_name]

    context = {
        'employee': employee_data,
        'courses': courses,
        'batches': batches,
        'my_nominations': my_nominations,
    }
    return render(request, 'portal/training_catalog.html', context)


@employee_portal_access
def development_plans(request, employee_data):
    if not employee_data:
        return redirect('portal_login')

    emp_email = employee_data.get('email', '')
    emp_name = employee_data.get('name', '')

    from hrm.models import Employee as SQLEmployee, DevelopmentPlan, TrainingNeed
    emp_obj = SQLEmployee.objects.filter(email=emp_email).first()

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'request_training_need' and emp_obj:
            try:
                TrainingNeed.objects.create(
                    employee=emp_obj,
                    skill_gap=request.POST.get('skill_gap', ''),
                    recommended_training=request.POST.get('recommended_training', ''),
                    priority=request.POST.get('priority', 'Medium'),
                    status='Identified',
                    created_by=request.user,
                )
                messages.success(request, "Training need submitted for review.")
            except Exception as e:
                hrm_logger.error(f"Training need request error: {e}")
                messages.error(request, "Failed to submit training need.")
        return redirect('portal:development_plans')

    plans = DevelopmentPlan.objects.filter(employee=emp_obj, is_active=True) if emp_obj else []
    needs = TrainingNeed.objects.filter(employee=emp_obj, is_active=True) if emp_obj else []

    context = {
        'employee': employee_data,
        'plans': plans,
        'needs': needs,
    }
    return render(request, 'portal/development_plans.html', context)


@employee_portal_access
def notifications(request, employee_data):
    if not employee_data:
        return redirect('portal_login')

    from hrm.models import Notification, NotificationPreference

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'mark_read':
            nid = request.POST.get('notification_id')
            if nid:
                Notification.objects.filter(id=nid, recipient=request.user).update(is_read=True)
        elif action == 'mark_all_read':
            Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        elif action == 'update_prefs':
            pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
            pref.notify_in_app = request.POST.get('notify_in_app') == 'on'
            pref.notify_email = request.POST.get('notify_email') == 'on'
            pref.save()
            messages.success(request, "Notification preferences updated.")
        return redirect('portal:notifications')

    notifications = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:100]
    unread_count = notifications.filter(is_read=False).count()
    pref, _ = NotificationPreference.objects.get_or_create(user=request.user)

    context = {
        'employee': employee_data,
        'notifications': notifications,
        'unread_count': unread_count,
        'prefs': pref,
    }
    return render(request, 'portal/notifications.html', context)


@employee_portal_access
def succession(request, employee_data):
    if not employee_data:
        return redirect('portal_login')

    from hrm.models import KeyPosition, SuccessorCandidate, SuccessionPlan

    emp_name = employee_data.get('name', '')
    emp_email = employee_data.get('email', '')

    # Find this employee's candidacy
    from hrm.models import Employee as SQLEmployee
    emp_obj = SQLEmployee.objects.filter(email=emp_email).first()
    my_candidates = SuccessorCandidate.objects.filter(
        employee=emp_obj, is_active=True
    ).select_related('key_position') if emp_obj else []

    # Key positions the employee might be a candidate for
    key_positions = KeyPosition.objects.filter(is_active=True)

    # Succession plans relevant to the employee's department
    emp_dept = employee_data.get('department', '')
    plans = SuccessionPlan.objects.filter(
        Q(department=emp_dept) | Q(department=''), is_active=True
    ) if emp_dept else SuccessionPlan.objects.filter(is_active=True)

    context = {
        'employee': employee_data,
        'my_candidates': my_candidates,
        'key_positions': key_positions,
        'plans': plans,
    }
    return render(request, 'portal/succession.html', context)


# ── Phase 5: Employee Skills & Education (Portal) ───────────────────

@employee_portal_access
def skills_inventory(request, employee_data):
    if not employee_data:
        return redirect('portal_login')
    from hrm.models import (
        Employee as SQLEmployee,
        EmployeeEducation, EmployeeExperience, EmployeeSkill,
        Competency, CompetencyRating,
    )
    emp_obj = SQLEmployee.objects.filter(email=employee_data.get('email', '')).first()

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'add_education' and emp_obj:
                EmployeeEducation.objects.create(
                    employee=emp_obj, degree=request.POST['degree'],
                    institution=request.POST['institution'],
                    field_of_study=request.POST.get('field_of_study', ''),
                    start_year=int(request.POST['start_year']) if request.POST.get('start_year') else None,
                    end_year=int(request.POST['end_year']) if request.POST.get('end_year') else None,
                    grade=request.POST.get('grade', ''),
                )
                messages.success(request, "Education added.")
            elif action == 'add_experience' and emp_obj:
                EmployeeExperience.objects.create(
                    employee=emp_obj, company=request.POST['company'],
                    job_title=request.POST['job_title'],
                    start_date=request.POST['start_date'],
                    end_date=request.POST.get('end_date') or None,
                    is_current=request.POST.get('is_current') == 'on',
                    description=request.POST.get('description', ''),
                )
                messages.success(request, "Experience added.")
            elif action == 'add_skill' and emp_obj:
                EmployeeSkill.objects.create(
                    employee=emp_obj, skill_name=request.POST['skill_name'],
                    proficiency=request.POST['proficiency'],
                    years_of_experience=request.POST.get('years_of_experience') or None,
                )
                messages.success(request, "Skill added.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('portal:skills_inventory')

    education = EmployeeEducation.objects.filter(employee=emp_obj, is_active=True) if emp_obj else []
    experiences = EmployeeExperience.objects.filter(employee=emp_obj, is_active=True) if emp_obj else []
    skills = EmployeeSkill.objects.filter(employee=emp_obj, is_active=True) if emp_obj else []
    competencies = Competency.objects.filter(is_active=True)
    comp_ratings = CompetencyRating.objects.filter(employee=emp_obj, is_active=True).select_related('competency') if emp_obj else []

    context = {
        'employee': employee_data, 'education': education, 'experiences': experiences,
        'skills': skills, 'competencies': competencies, 'comp_ratings': comp_ratings,
    }
    return render(request, 'portal/skills_inventory.html', context)


# ── Phase 5: 360 Feedback (Portal) ─────────────────────────────────

@employee_portal_access
def feedback_360(request, employee_data):
    if not employee_data:
        return redirect('portal_login')
    from hrm.models import Employee as SQLEmployee, FeedbackRequest, FeedbackResponse, FeedbackQuestion

    emp_obj = SQLEmployee.objects.filter(email=employee_data.get('email', '')).first()

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'submit_response':
                req = FeedbackRequest.objects.get(id=request.POST.get('request_id'))
                for key, val in request.POST.items():
                    if key.startswith('q_'):
                        qid = key.split('_', 1)[1]
                        FeedbackResponse.objects.update_or_create(
                            request=req, question_id=qid,
                            defaults={'rating': int(val) if val.isdigit() else None,
                                      'response_text': val if not val.isdigit() else ''},
                        )
                req.status = 'Completed'
                req.save()
                messages.success(request, "Feedback submitted.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('portal:feedback_360')

    my_requests = FeedbackRequest.objects.filter(
        reviewee=emp_obj, is_active=True
    ).select_related('reviewer', 'review_cycle') if emp_obj else []
    questions = FeedbackQuestion.objects.filter(is_active=True)

    context = {'employee': employee_data, 'my_requests': my_requests, 'questions': questions}
    return render(request, 'portal/feedback_360.html', context)


# ── Phase 5: Engagement Surveys (Portal) ────────────────────────────

@employee_portal_access
def surveys(request, employee_data):
    if not employee_data:
        return redirect('portal_login')
    from hrm.models import Employee as SQLEmployee, EngagementSurvey, SurveyQuestion, SurveyResponse

    emp_obj = SQLEmployee.objects.filter(email=employee_data.get('email', '')).first()

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'submit_survey':
                survey = EngagementSurvey.objects.get(id=request.POST.get('survey_id'))
                for key, val in request.POST.items():
                    if key.startswith('sq_'):
                        qid = key.split('_', 1)[1]
                        SurveyResponse.objects.create(
                            survey=survey, question_id=qid,
                            employee=emp_obj,
                            response_value=int(val) if val.isdigit() else None,
                            response_text=val if not val.isdigit() else '',
                        )
                messages.success(request, "Survey response submitted.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('portal:surveys')

    active_surveys = EngagementSurvey.objects.filter(status='Active', is_active=True)
    my_responses = SurveyResponse.objects.filter(employee=emp_obj).values_list('survey_id', flat=True).distinct() if emp_obj else []

    context = {
        'employee': employee_data, 'active_surveys': active_surveys,
        'my_responses': my_responses,
    }
    return render(request, 'portal/surveys.html', context)


# ── Phase 5: Compliance Calendar (Portal) ───────────────────────────

@employee_portal_access
def compliance_calendar(request, employee_data):
    if not employee_data:
        return redirect('portal_login')
    from hrm.models import Employee as SQLEmployee, ComplianceReminder
    from hrm.services import sync_document_compliance_reminders, check_compliance_overdue_reminders

    sync_document_compliance_reminders()
    check_compliance_overdue_reminders()

    emp_obj = SQLEmployee.objects.filter(email=employee_data.get('email', '')).first()

    if request.method == 'POST' and emp_obj:
        action = request.POST.get('action')
        try:
            if action == 'complete_reminder':
                reminder = ComplianceReminder.objects.get(
                    id=request.POST.get('reminder_id'), employee=emp_obj
                )
                reminder.mark_completed()
                messages.success(request, "Reminder marked complete.")
            elif action == 'update_reminder':
                reminder, _ = ComplianceReminder.objects.get_or_create(
                    employee=emp_obj,
                    reminder_type=request.POST.get('reminder_type', 'Other'),
                    defaults={
                        'title': request.POST.get('title', ''),
                        'description': request.POST.get('description', ''),
                        'due_date': request.POST.get('due_date'),
                    }
                )
                messages.success(request, "Reminder saved.")
        except Exception as e:
            messages.error(request, f"Error: {e}")
        return redirect('portal:compliance_calendar')

    reminders = ComplianceReminder.objects.filter(employee=emp_obj, is_active=True) if emp_obj else []

    context = {'employee': employee_data, 'reminders': reminders}
    return render(request, 'portal/compliance_calendar.html', context)


# ── Phase 5: Talent Review / 9-Box (Portal) ────────────────────────

@employee_portal_access
def talent_review(request, employee_data):
    if not employee_data:
        return redirect('portal_login')
    from hrm.models import Employee as SQLEmployee, TalentReviewMeeting, NineBoxCell

    emp_obj = SQLEmployee.objects.filter(email=employee_data.get('email', '')).first()

    meetings = TalentReviewMeeting.objects.filter(is_active=True, status='Completed')
    cells = NineBoxCell.objects.filter(is_active=True).select_related('talent_review', 'employee')
    my_cell = cells.filter(employee=emp_obj).first() if emp_obj else None

    context = {
        'employee': employee_data,
        'meetings': meetings,
        'cells': cells,
        'my_cell': my_cell,
        'emp_obj': emp_obj,
    }
    return render(request, 'portal/talent_review.html', context)
