from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import date, datetime, timedelta
from django.db.models import Q, Sum as SumAgg

from accounts.decorators import employee_portal_access
from config.logger import hrm_logger
from config.services.event_bus import event_bus

from hrm.models import (
    Employee, Leave, LeaveBalance, Holiday,
    Attendance, PerformanceReview, PerformanceImprovementPlan,
    Document, Asset, PayrollEmployee, AdvanceSalary, ExpenseClaim, EmployeeShift,
    TrainingNeed, DevelopmentPlan, TrainingNomination,
    Notification, NotificationPreference,
    KeyPosition, SuccessorCandidate, SuccessionPlan,
    EmployeeEducation, EmployeeExperience, EmployeeSkill,
    Competency, CompetencyRating,
    FeedbackRequest, FeedbackResponse, FeedbackQuestion,
    EngagementSurvey, SurveyResponse,
    ComplianceReminder, TalentReviewMeeting, NineBoxCell,
)


@employee_portal_access
def dashboard(request, employee_data, emp_obj):
    if not employee_data or not emp_obj:
        return redirect('portal_login')

    try:
        today = date.today()
        month_start = today.replace(day=1)

        # Attendance this month
        month_attendance = Attendance.objects.filter(
            employee=emp_obj, date__gte=month_start, date__lte=today
        )
        present_count = month_attendance.filter(status='Present').count()
        absent_count = month_attendance.filter(status='Absent').count()
        late_count = month_attendance.filter(status='Late').count()

        # Pending leave requests
        pending_leaves = Leave.objects.filter(
            employee=emp_obj, status='Pending', is_active=True
        ).count()

        # Performance reviews
        total_reviews = PerformanceReview.objects.filter(
            employee=emp_obj, is_active=True
        ).count()

        # Recent leaves
        recent_leaves = Leave.objects.filter(
            employee=emp_obj, is_active=True
        ).order_by('-from_date')[:5]

        # Upcoming holidays
        upcoming_holidays = Holiday.objects.filter(
            from_date__gte=today, is_active=True
        ).order_by('from_date')[:5]

        # Leave balances
        balances = LeaveBalance.objects.filter(
            employee=emp_obj, is_active=True
        )

        # Today's attendance for check-in/check-out
        today_attendance = Attendance.objects.filter(
            employee=emp_obj, date=today
        ).first()

    except Exception as e:
        hrm_logger.error(f"Portal dashboard error: {e}")
        present_count = absent_count = late_count = 0
        pending_leaves = total_reviews = 0
        recent_leaves = upcoming_holidays = balances = []
        today_attendance = None

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'pending_leaves': pending_leaves,
        'total_reviews': total_reviews,
        'recent_leaves': recent_leaves,
        'upcoming_holidays': upcoming_holidays,
        'balances': balances,
        'today_attendance': today_attendance,
    }
    return render(request, 'portal/dashboard.html', context)


@employee_portal_access
def profile(request, employee_data, emp_obj):
    if not employee_data:
        return redirect('portal_login')

    if request.method == 'POST':
        try:
            from config.firebase import db
            doc_id = employee_data.get('id')
            updates = {}
            fields = [
                'phone', 'alt_phone', 'city', 'zip',
                'ec_primary_name', 'ec_primary_relation', 'ec_primary_mobile',
                'ec_secondary_name', 'ec_secondary_relation', 'ec_secondary_mobile',
            ]
            for f in fields:
                val = request.POST.get(f, '').strip()
                if val:
                    updates[f] = val
            if updates and doc_id:
                db.collection('hrm_employees').document(doc_id).update(updates)
                # Dual-write to Django ORM
                orm_fields = {
                    'phone': 'phone',
                    'alt_phone': 'alt_phone',
                    'city': 'city',
                    'zip': 'zip',
                    'ec_primary_name': 'ec_primary_name',
                    'ec_primary_relation': 'ec_primary_relation',
                    'ec_primary_mobile': 'ec_primary_mobile',
                    'ec_secondary_name': 'ec_secondary_name',
                    'ec_secondary_relation': 'ec_secondary_relation',
                    'ec_secondary_mobile': 'ec_secondary_mobile',
                }
                orm_changed = False
                for post_key, orm_attr in orm_fields.items():
                    if post_key in updates:
                        setattr(emp_obj, orm_attr, updates[post_key])
                        orm_changed = True
                if orm_changed:
                    emp_obj.save(update_fields=list(orm_fields.values()))
                messages.success(request, "Profile updated successfully.")
                doc = db.collection('hrm_employees').document(doc_id).get()
                if doc.exists:
                    employee_data = doc.to_dict()
                    employee_data['id'] = doc.id
        except Exception as e:
            hrm_logger.error(f"Portal profile update error: {e}")
            messages.error(request, "Failed to update profile.")
        return redirect('portal:profile')

    context = {'employee': employee_data, 'emp_obj': emp_obj}
    return render(request, 'portal/profile.html', context)


@employee_portal_access
def attendance(request, employee_data, emp_obj):
    if not employee_data or not emp_obj:
        return redirect('portal_login')

    today = date.today()

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action in ('check_in', 'check_out'):
            now = datetime.now()
            att = Attendance.objects.filter(employee=emp_obj, date=today).first()
            if action == 'check_in':
                if att and att.check_in:
                    messages.warning(request, 'You have already checked in today.')
                else:
                    if not att:
                        att = Attendance(employee=emp_obj, date=today, status='Present')
                    att.check_in = now.time()
                    att.save()
                    messages.success(request, f'Checked in at {now.strftime("%H:%M")}.')
            elif action == 'check_out':
                if not att or not att.check_in:
                    messages.error(request, 'You must check in first.')
                elif att.check_out:
                    messages.warning(request, 'You have already checked out today.')
                else:
                    att.check_out = now.time()
                    att.save()
                    messages.success(request, f'Checked out at {now.strftime("%H:%M")}.')
        return redirect('portal:attendance')
    month_param = request.GET.get('month', '')

    if month_param:
        try:
            year, mon = month_param.split('-')
            month_start = date(int(year), int(mon), 1)
        except (ValueError, IndexError):
            month_start = today.replace(day=1)
    else:
        month_start = today.replace(day=1)

    if month_start.month == 12:
        month_end = date(month_start.year + 1, 1, 1)
        next_month = month_end
    else:
        month_end = date(month_start.year, month_start.month + 1, 1)
    prev_month = date(month_start.year, month_start.month - 1, 1) if month_start.month > 1 else date(month_start.year - 1, 12, 1)

    logs = Attendance.objects.filter(
        employee=emp_obj, is_active=True,
        date__gte=month_start, date__lt=month_end,
    ).order_by('-date')

    month_label = month_start.strftime('%B %Y')

    # Stats for the month
    present_count = sum(1 for l in logs if l.status == 'Present')
    absent_count = sum(1 for l in logs if l.status == 'Absent')
    late_count = sum(1 for l in logs if l.status == 'Late')

    # Today's attendance for check-in/check-out
    today_attendance = Attendance.objects.filter(
        employee=emp_obj, date=today
    ).first()

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'logs': logs,
        'month_start': month_start,
        'month_label': month_label,
        'prev_month': prev_month.strftime('%Y-%m'),
        'next_month': next_month.strftime('%Y-%m'),
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'today_attendance': today_attendance,
    }
    return render(request, 'portal/attendance.html', context)


@employee_portal_access
def roster(request, employee_data, emp_obj):
    if not employee_data or not emp_obj:
        return redirect('portal_login')

    today = date.today()
    week_param = request.GET.get('week', '')

    if week_param:
        try:
            week_start = date.fromisoformat(week_param)
        except ValueError:
            week_start = today
    else:
        week_start = today

    # Snap to Monday
    week_start = week_start - timedelta(days=week_start.weekday())
    week_end = week_start + timedelta(days=6)

    # Build day-by-day data
    week_days = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        shift = EmployeeShift.objects.filter(
            employee=emp_obj, is_active=True,
            start_date__lte=day,
        ).filter(
            Q(end_date__gte=day) | Q(end_date__isnull=True)
        ).first()
        att = Attendance.objects.filter(employee=emp_obj, date=day).first()
        week_days.append({
            'date': day,
            'is_today': day == today,
            'is_past': day < today,
            'shift_name': shift.shift_name if shift else None,
            'check_in': att.check_in if att else None,
            'check_out': att.check_out if att else None,
            'status': att.status if att else None,
        })

    prev_week = week_start - timedelta(days=7)
    next_week = week_start + timedelta(days=7)

    # Current active shift
    current_shift = EmployeeShift.objects.filter(
        employee=emp_obj, is_active=True,
        start_date__lte=today,
    ).filter(
        Q(end_date__gte=today) | Q(end_date__isnull=True)
    ).first()

    # Upcoming shifts
    upcoming_shifts = EmployeeShift.objects.filter(
        employee=emp_obj, is_active=True,
        start_date__gt=today,
    ).order_by('start_date')[:5]

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'week_days': week_days,
        'week_start': week_start,
        'week_end': week_end,
        'prev_week': prev_week.isoformat(),
        'next_week': next_week.isoformat(),
        'current_shift': current_shift,
        'upcoming_shifts': upcoming_shifts,
    }
    return render(request, 'portal/roster.html', context)


@employee_portal_access
def leave(request, employee_data, emp_obj):
    if not employee_data or not emp_obj:
        return redirect('portal_login')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'apply_leave':
            try:
                from_date_str = request.POST.get('from_date', '')
                to_date_str = request.POST.get('to_date', '')
                leave_type = request.POST.get('leave_type', '')
                reason = request.POST.get('reason', '')

                fd = date.fromisoformat(from_date_str)
                td = date.fromisoformat(to_date_str)

                if td < fd:
                    messages.error(request, "To date must be after from date.")
                    return redirect('portal:leave')

                days = (td - fd).days + 1
                duration = f"{days} Day{'s' if days != 1 else ''}"

                # Check leave balance
                balance = LeaveBalance.objects.filter(
                    employee=emp_obj, leave_type=leave_type, is_active=True
                ).first()
                if balance and days > balance.available:
                    messages.error(request, f"Insufficient {leave_type} leave balance. You have {balance.available} day(s) available but requested {days}.")
                    return redirect('portal:leave')

                leave_obj = Leave.objects.create(
                    employee=emp_obj,
                    leave_type=leave_type,
                    from_date=fd,
                    to_date=td,
                    duration=duration,
                    reason=reason,
                    status='Pending',
                    created_by=request.user,
                )

                # Update pending count on balance
                if balance:
                    balance.pending = balance.pending + days
                    balance.save()

                # Handle medical certificate upload for sick leave
                if leave_type == 'Sick' and request.FILES.get('attachment'):
                    from hrm.models import Document as HrmDocument
                    try:
                        uploaded_file = request.FILES['attachment']
                        HrmDocument.objects.create(
                            employee=emp_obj,
                            document_type='Medical Certificate',
                            document_number=str(leave_obj.id),
                            file=uploaded_file,
                            is_active=True,
                        )
                    except Exception as e:
                        hrm_logger.error(f"Medical certificate upload error: {e}")

                # Fire notification event
                try:
                    event_bus.publish('leave.applied', {
                        'employee_name': employee_data.get('name', ''),
                        'employee_email': emp_obj.email or '',
                        'leave_type': leave_type,
                        'duration': duration,
                        'doc_id': str(leave_obj.id),
                        'applied_by': request.user.username,
                    })
                except Exception:
                    pass

                messages.success(request, "Leave request submitted successfully.")
            except Exception as e:
                hrm_logger.error(f"Portal leave apply error: {e}")
                messages.error(request, "Failed to submit leave request.")

        elif action == 'cancel_leave':
            leave_id = request.POST.get('leave_id')
            if leave_id:
                try:
                    leave_obj = Leave.objects.get(
                        id=leave_id, employee=emp_obj, status='Pending', is_active=True
                    )
                    requested_days = (leave_obj.to_date - leave_obj.from_date).days + 1
                    balance = LeaveBalance.objects.filter(
                        employee=emp_obj, leave_type=leave_obj.leave_type, is_active=True
                    ).first()
                    if balance:
                        balance.pending = max(0, balance.pending - requested_days)
                        balance.save()
                    leave_obj.is_active = False
                    leave_obj.save()
                    messages.success(request, "Leave request cancelled.")
                except Leave.DoesNotExist:
                    messages.error(request, "Leave request not found or already processed.")
                except Exception as e:
                    hrm_logger.error(f"Portal leave cancel error: {e}")
                    messages.error(request, "Failed to cancel leave.")

        return redirect('portal:leave')

    my_leaves = Leave.objects.filter(employee=emp_obj, is_active=True).order_by('-from_date')
    holidays = Holiday.objects.filter(is_active=True).order_by('from_date')
    balances = LeaveBalance.objects.filter(employee=emp_obj, is_active=True)

    # Annotate leaves with their medical certificate attachment
    from hrm.models import Document as HrmDocument
    leave_ids_list = [str(lv.id) for lv in my_leaves]
    all_attachments = HrmDocument.objects.filter(
        employee=emp_obj, document_type='Medical Certificate',
        document_number__in=leave_ids_list, is_active=True
    )
    att_map = {doc.document_number: doc for doc in all_attachments}
    for lv in my_leaves:
        lv._attachment = att_map.get(str(lv.id))

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'leaves': my_leaves,
        'holidays': holidays,
        'balances': balances,
    }
    return render(request, 'portal/leave.html', context)


@employee_portal_access
def payslips(request, employee_data, emp_obj):
    if not employee_data or not emp_obj:
        return redirect('portal_login')

    # Get all available periods for the filter dropdown
    all_periods = PayrollEmployee.objects.filter(
        employee=emp_obj
    ).select_related('payroll').values_list(
        'payroll__period', flat=True
    ).distinct().order_by('-payroll__period')

    period = request.GET.get('period', '')

    base_qs = PayrollEmployee.objects.filter(employee=emp_obj).select_related('payroll')
    if period:
        base_qs = base_qs.filter(payroll__period=period)

    entries = base_qs.order_by('-payroll__created_at')

    # Enrich each entry with advance deductions for the same period
    enriched = []
    for e in entries:
        advance_deductions = AdvanceSalary.objects.filter(
            employee=emp_obj,
            deduct_month=e.payroll.period,
            status='Deducted',
            is_active=True,
        ).aggregate(total=SumAgg('amount'))['total'] or 0
        enriched.append({
            'entry': e,
            'advance_deduction': advance_deductions,
        })

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'entries': enriched,
        'all_periods': all_periods,
        'selected_period': period,
    }
    return render(request, 'portal/payslips.html', context)


@employee_portal_access
def advance_salary(request, employee_data, emp_obj):
    if not employee_data or not emp_obj:
        return redirect('portal_login')

    # Tenure-based eligibility
    from dateutil.relativedelta import relativedelta
    today = date.today()
    joining = emp_obj.joining_date
    if joining:
        tenure_months = (today.year - joining.year) * 12 + (today.month - joining.month)
        if tenure_months < 6:
            tenure_limit_pct = 0
        elif tenure_months < 12:
            tenure_limit_pct = 0.25
        elif tenure_months < 24:
            tenure_limit_pct = 0.35
        else:
            tenure_limit_pct = 0.50
    else:
        tenure_limit_pct = 0.50

    max_amount = float(emp_obj.basic_salary or 0) * tenure_limit_pct
    has_pending = AdvanceSalary.objects.filter(
        employee=emp_obj, status='Pending', is_active=True
    ).exists()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'apply_advance':
            try:
                amount = request.POST.get('amount', '')
                deduct_month = request.POST.get('deduct_month', '')
                reason = request.POST.get('reason', '')

                if not amount or not deduct_month:
                    messages.error(request, "Amount and deduction month are required.")
                    return redirect('portal:advance_salary')

                amount_val = float(amount)
                if amount_val <= 0:
                    messages.error(request, "Amount must be greater than zero.")
                    return redirect('portal:advance_salary')

                if amount_val > max_amount:
                    messages.error(
                        request,
                        f"Maximum advance amount is {max_amount:,.2f} (50% of basic salary)."
                    )
                    return redirect('portal:advance_salary')

                if has_pending:
                    messages.error(request, "You already have a pending advance request.")
                    return redirect('portal:advance_salary')

                advance = AdvanceSalary.objects.create(
                    employee=emp_obj,
                    amount=amount_val,
                    deduct_month=deduct_month,
                    reason=reason,
                    status='Pending',
                    created_by=request.user,
                )

                try:
                    event_bus.publish('advance_salary.applied', {
                        'employee_name': employee_data.get('name', ''),
                        'employee_email': emp_obj.email or '',
                        'amount': str(amount_val),
                        'deduct_month': deduct_month,
                        'doc_id': str(advance.id),
                        'applied_by': request.user.username,
                    })
                except Exception:
                    pass

                messages.success(request, "Advance salary request submitted successfully.")
            except (ValueError, TypeError):
                messages.error(request, "Invalid amount. Please enter a valid number.")
            except Exception as e:
                hrm_logger.error(f"Portal advance salary error: {e}")
                messages.error(request, "Failed to submit advance request.")
        return redirect('portal:advance_salary')

    my_advances = AdvanceSalary.objects.filter(
        employee=emp_obj, is_active=True
    ).order_by('-created_at')

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'advances': my_advances,
        'max_amount': max_amount,
        'has_pending': has_pending,
        'next_month': date.today().replace(day=1),
    }
    return render(request, 'portal/advance_salary.html', context)


@employee_portal_access
def performance(request, employee_data, emp_obj):
    if not employee_data or not emp_obj:
        return redirect('portal_login')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'submit_self_assessment':
            try:
                review_id = request.POST.get('review_id')
                strengths = request.POST.get('strengths', '')
                improvements = request.POST.get('improvements', '')
                goals = request.POST.get('goals', '')
                if review_id:
                    PerformanceReview.objects.filter(
                        id=review_id, employee=emp_obj, status='Self-Assessment'
                    ).update(
                        strengths=strengths,
                        improvements=improvements,
                        goals=goals,
                        status='Manager-Review',
                    )
                    messages.success(request, "Self-assessment submitted successfully.")
            except Exception as e:
                hrm_logger.error(f"Portal self-assessment error: {e}")
                messages.error(request, "Failed to submit self-assessment.")
        return redirect('portal:performance')

    reviews = PerformanceReview.objects.filter(
        employee=emp_obj, is_active=True
    ).select_related('review_cycle', 'reviewer').order_by('-created_at')

    pips = PerformanceImprovementPlan.objects.filter(
        employee=emp_obj, is_active=True
    ).order_by('-created_at')

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'reviews': reviews,
        'pips': pips,
    }
    return render(request, 'portal/performance.html', context)


@employee_portal_access
def documents(request, employee_data, emp_obj):
    if not employee_data or not emp_obj:
        return redirect('portal_login')

    my_docs = Document.objects.filter(employee=emp_obj, is_active=True)
    my_assets = Asset.objects.filter(employee=emp_obj, is_active=True)

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'documents': my_docs,
        'assets': my_assets,
    }
    return render(request, 'portal/documents.html', context)


@employee_portal_access
def training_catalog(request, employee_data, emp_obj):
    if not employee_data or not emp_obj:
        return redirect('portal_login')

    emp_email = employee_data.get('email', '')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'express_interest':
            try:
                course_name = request.POST.get('course_name', '')
                course_provider = request.POST.get('course_provider', '')
                TrainingNomination.objects.create(
                    employee=emp_obj,
                    course_name=course_name or request.POST.get('course_name', 'Training Course'),
                    provider=course_provider,
                    status='Nominated',
                    created_by=request.user,
                )
                messages.success(request, f"Interest registered for training.")
            except Exception as e:
                hrm_logger.error(f"Training interest error: {e}")
                messages.error(request, "Failed to register interest.")
        return redirect('portal:training_catalog')

    my_nominations = TrainingNomination.objects.filter(
        employee=emp_obj, is_active=True
    ).order_by('-created_at')

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'my_nominations': my_nominations,
    }
    return render(request, 'portal/training_catalog.html', context)


@employee_portal_access
def development_plans(request, employee_data, emp_obj):
    if not employee_data:
        return redirect('portal_login')

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
        'emp_obj': emp_obj,
        'plans': plans,
        'needs': needs,
    }
    return render(request, 'portal/development_plans.html', context)


@employee_portal_access
def notifications(request, employee_data, emp_obj):
    if not employee_data:
        return redirect('portal_login')

    if request.method == 'POST':
        action = request.POST.get('action')
        from django.utils import timezone
        if action == 'mark_read':
            nid = request.POST.get('notification_id')
            if nid:
                Notification.objects.filter(id=nid, recipient=request.user).update(
                    is_read=True, read_at=timezone.now()
                )
        elif action == 'mark_all_read':
            Notification.objects.filter(recipient=request.user, is_read=False).update(
                is_read=True, read_at=timezone.now()
            )
        elif action == 'update_prefs':
            pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
            pref.notify_in_app = request.POST.get('notify_in_app') == 'on'
            pref.notify_email = request.POST.get('notify_email') == 'on'
            pref.save()
            messages.success(request, "Notification preferences updated.")
        return redirect('portal:notifications')

    filter_mode = request.GET.get('filter', 'all')
    base_qs = Notification.objects.filter(recipient=request.user, is_active=True).order_by('-created_at')
    if filter_mode == 'unread':
        notifications = base_qs.filter(is_read=False)
    elif filter_mode == 'read':
        notifications = base_qs.filter(is_read=True)
    else:
        notifications = base_qs

    notifications = notifications[:100]
    unread_count = base_qs.filter(is_read=False).count()
    pref, _ = NotificationPreference.objects.get_or_create(user=request.user)

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'notifications': notifications,
        'unread_count': unread_count,
        'prefs': pref,
        'filter_mode': filter_mode,
    }
    return render(request, 'portal/notifications.html', context)


@employee_portal_access
def succession(request, employee_data, emp_obj):
    if not employee_data:
        return redirect('portal_login')

    my_candidates = SuccessorCandidate.objects.filter(
        employee=emp_obj, is_active=True
    ).select_related('key_position') if emp_obj else []

    key_positions = KeyPosition.objects.filter(is_active=True)

    emp_dept = employee_data.get('department', '')
    plans = SuccessionPlan.objects.filter(
        Q(department=emp_dept) | Q(department=''), is_active=True
    ) if emp_dept else SuccessionPlan.objects.filter(is_active=True)

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'my_candidates': my_candidates,
        'key_positions': key_positions,
        'plans': plans,
    }
    return render(request, 'portal/succession.html', context)


# ── Employee Skills & Education ───────────────────

@employee_portal_access
def skills_inventory(request, employee_data, emp_obj):
    if not employee_data:
        return redirect('portal_login')

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
        'employee': employee_data, 'emp_obj': emp_obj,
        'education': education, 'experiences': experiences,
        'skills': skills, 'competencies': competencies, 'comp_ratings': comp_ratings,
    }
    return render(request, 'portal/skills_inventory.html', context)


# ── 360 Feedback ─────────────────────────────────

@employee_portal_access
def feedback_360(request, employee_data, emp_obj):
    if not employee_data:
        return redirect('portal_login')

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
                            defaults={
                                'rating': int(val) if val.isdigit() else None,
                                'response_text': val if not val.isdigit() else '',
                            },
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

    context = {'employee': employee_data, 'emp_obj': emp_obj, 'my_requests': my_requests, 'questions': questions}
    return render(request, 'portal/feedback_360.html', context)


# ── Engagement Surveys ────────────────────────────

@employee_portal_access
def surveys(request, employee_data, emp_obj):
    if not employee_data:
        return redirect('portal_login')

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
        'employee': employee_data, 'emp_obj': emp_obj,
        'active_surveys': active_surveys,
        'my_responses': my_responses,
    }
    return render(request, 'portal/surveys.html', context)


# ── Compliance Calendar ───────────────────────────

@employee_portal_access
def compliance_calendar(request, employee_data, emp_obj):
    if not employee_data:
        return redirect('portal_login')
    from hrm.services import sync_document_compliance_reminders, check_compliance_overdue_reminders

    sync_document_compliance_reminders()
    check_compliance_overdue_reminders()

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

    context = {'employee': employee_data, 'emp_obj': emp_obj, 'reminders': reminders}
    return render(request, 'portal/compliance_calendar.html', context)


# ── Talent Review / 9-Box ────────────────────────

@employee_portal_access
def talent_review(request, employee_data, emp_obj):
    if not employee_data:
        return redirect('portal_login')

    meetings = TalentReviewMeeting.objects.filter(is_active=True, status='Completed')
    cells = NineBoxCell.objects.filter(is_active=True).select_related('talent_review', 'employee')
    my_cell = cells.filter(employee=emp_obj).first() if emp_obj else None

    box_levels = ['High', 'Medium', 'Low']

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'meetings': meetings,
        'cells': cells,
        'my_cell': my_cell,
        'perf_levels': box_levels,
        'pot_levels': box_levels,
    }
    return render(request, 'portal/talent_review.html', context)


@employee_portal_access
def approvals(request, employee_data, emp_obj):
    if not employee_data or not emp_obj:
        return redirect('portal_login')

    direct_reports = Employee.objects.filter(reporting_to=emp_obj, is_active=True)
    is_manager = direct_reports.exists()

    pending_leaves = Leave.objects.none()
    pending_advances = AdvanceSalary.objects.none()
    pending_expenses = ExpenseClaim.objects.none()

    if is_manager:
        pending_leaves = Leave.objects.filter(
            employee__in=direct_reports, status='Pending', is_active=True
        ).order_by('-from_date')

        pending_advances = AdvanceSalary.objects.filter(
            employee__in=direct_reports, status='Pending', is_active=True
        ).order_by('-created_at')

        pending_expenses = ExpenseClaim.objects.filter(
            employee__in=direct_reports, status='Pending', is_active=True
        ).order_by('-created_at')

    if request.method == 'POST':
        action = request.POST.get('action', '')
        request_id = request.POST.get('request_id', '')

        if not is_manager:
            messages.error(request, 'You are not authorized to perform this action.')
            return redirect('portal:approvals')

        try:
            if action == 'approve_leave':
                obj = Leave.objects.get(id=request_id, employee__in=direct_reports, status='Pending')
                obj.status = 'Approved'
                obj.updated_by = request.user
                obj.save()

                event_bus.publish('leave.approved', {
                    'employee_name': obj.employee.name,
                    'employee_email': obj.employee.email,
                    'leave_type': obj.leave_type,
                    'duration': obj.duration,
                    'doc_id': str(obj.id),
                    'approved_by': request.user.username,
                })
                messages.success(request, f"Leave request from {obj.employee.name} approved.")

            elif action == 'reject_leave':
                obj = Leave.objects.get(id=request_id, employee__in=direct_reports, status='Pending')
                obj.status = 'Rejected'
                obj.updated_by = request.user
                obj.save()

                rejection_reason = request.POST.get('rejection_reason', '').strip()

                event_bus.publish('leave.rejected', {
                    'employee_name': obj.employee.name,
                    'employee_email': obj.employee.email,
                    'leave_type': obj.leave_type,
                    'duration': obj.duration,
                    'doc_id': str(obj.id),
                    'rejected_by': request.user.username,
                    'rejection_reason': rejection_reason,
                })
                msg = f"Leave request from {obj.employee.name} rejected."
                if rejection_reason:
                    msg += f" Reason: {rejection_reason}"
                messages.success(request, msg)

            elif action == 'approve_advance':
                obj = AdvanceSalary.objects.get(id=request_id, employee__in=direct_reports, status='Pending')
                obj.status = 'Approved'
                obj.updated_by = request.user
                obj.save()

                event_bus.publish('advance_salary.approved', {
                    'employee_name': obj.employee.name,
                    'employee_email': obj.employee.email,
                    'amount': str(obj.amount),
                    'deduct_month': obj.deduct_month,
                    'doc_id': str(obj.id),
                    'approved_by': request.user.username,
                })
                messages.success(request, f"Advance salary from {obj.employee.name} approved.")

            elif action == 'reject_advance':
                obj = AdvanceSalary.objects.get(id=request_id, employee__in=direct_reports, status='Pending')
                obj.status = 'Rejected'
                obj.updated_by = request.user
                obj.save()

                rejection_reason = request.POST.get('rejection_reason', '').strip()

                event_bus.publish('advance_salary.rejected', {
                    'employee_name': obj.employee.name,
                    'employee_email': obj.employee.email,
                    'amount': str(obj.amount),
                    'deduct_month': obj.deduct_month,
                    'doc_id': str(obj.id),
                    'rejected_by': request.user.username,
                    'rejection_reason': rejection_reason,
                })
                msg = f"Advance salary from {obj.employee.name} rejected."
                if rejection_reason:
                    msg += f" Reason: {rejection_reason}"
                messages.success(request, msg)

            elif action == 'approve_expense':
                obj = ExpenseClaim.objects.get(id=request_id, employee__in=direct_reports, status='Pending')
                obj.status = 'Approved'
                obj.updated_by = request.user
                obj.save()

                event_bus.publish('expense_claim.approved', {
                    'employee_name': obj.employee.name,
                    'employee_email': obj.employee.email,
                    'amount': str(obj.amount),
                    'category': obj.category,
                    'doc_id': str(obj.id),
                    'approved_by': request.user.username,
                })
                messages.success(request, f"Expense claim from {obj.employee.name} approved.")

            elif action == 'reject_expense':
                obj = ExpenseClaim.objects.get(id=request_id, employee__in=direct_reports, status='Pending')
                obj.status = 'Rejected'
                obj.updated_by = request.user
                obj.save()

                rejection_reason = request.POST.get('rejection_reason', '').strip()

                event_bus.publish('expense_claim.rejected', {
                    'employee_name': obj.employee.name,
                    'employee_email': obj.employee.email,
                    'amount': str(obj.amount),
                    'category': obj.category,
                    'doc_id': str(obj.id),
                    'rejected_by': request.user.username,
                    'rejection_reason': rejection_reason,
                })
                msg = f"Expense claim from {obj.employee.name} rejected."
                if rejection_reason:
                    msg += f" Reason: {rejection_reason}"
                messages.success(request, msg)

            else:
                messages.error(request, 'Unknown action.')

        except Leave.DoesNotExist:
            messages.error(request, 'Leave request not found or already processed.')
        except AdvanceSalary.DoesNotExist:
            messages.error(request, 'Advance salary request not found or already processed.')
        except ExpenseClaim.DoesNotExist:
            messages.error(request, 'Expense claim not found or already processed.')
        except Exception as e:
            hrm_logger.error(f"Approval action error: {e}")
            messages.error(request, 'An error occurred while processing the action.')

        return redirect('portal:approvals')

    context = {
        'employee': employee_data,
        'emp_obj': emp_obj,
        'is_manager': is_manager,
        'pending_leaves': pending_leaves,
        'pending_advances': pending_advances,
        'pending_expenses': pending_expenses,
    }
    return render(request, 'portal/approvals.html', context)