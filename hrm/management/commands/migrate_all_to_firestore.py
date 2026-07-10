from django.core.management.base import BaseCommand
from django.utils import timezone
from config.firebase import db
from google.cloud.firestore import SERVER_TIMESTAMP
from hrm import models


def _safe_str(val):
    if val is None:
        return None
    if hasattr(val, 'isoformat'):
        return val.isoformat()
    return str(val)


def _user_ref(user):
    return f'users/{user.id}' if user else None


class Command(BaseCommand):
    help = 'Migrate all SQLite-only HRM data to Firestore collections'

    def handle(self, *args, **options):
        now = timezone.now()
        migrated = 0

        # ── 1. Disciplinary ──────────────────────────────────────────────
        self.stdout.write('Migrating Disciplinary...')
        cases = models.DisciplinaryCase.objects.filter(is_active=True).select_related('employee', 'reported_by')
        for case in cases:
            hearings = list(models.DisciplinaryHearing.objects.filter(case=case, is_active=True).values(
                'hearing_date', 'panel_members', 'location', 'notes', 'outcome', 'status'
            ))
            actions = list(models.DisciplinaryAction.objects.filter(case=case, is_active=True).values(
                'action_type', 'description', 'issued_date', 'effective_date',
                'expiry_date', 'status', 'supporting_document'
            ))
            db.collection('hrm_disciplinary_cases').document(str(case.id)).set({
                'employee': f'hrm_employees/{case.employee.firestore_id}' if case.employee and case.employee.firestore_id else None,
                'employee_name': case.employee.name if case.employee else '',
                'case_number': case.case_number,
                'incident_date': _safe_str(case.incident_date),
                'nature_of_offense': case.nature_of_offense,
                'severity': case.severity,
                'description': case.description,
                'status': case.status,
                'resolution': case.resolution,
                'resolved_date': _safe_str(case.resolved_date),
                'reported_by': _user_ref(case.reported_by),
                'is_active': case.is_active,
                'created_at': case.created_at.isoformat() if case.created_at else None,
                'updated_at': case.updated_at.isoformat() if case.updated_at else None,
                'hearings': [
                    {'id': f'h_{i}', 'hearing_date': _safe_str(h['hearing_date']),
                     'panel_members': h['panel_members'] or '', 'location': h['location'] or '',
                     'notes': h['notes'] or '', 'outcome': h['outcome'] or '', 'status': h['status']}
                    for i, h in enumerate(hearings)
                ],
                'actions': [
                    {'id': f'a_{i}', 'action_type': a['action_type'],
                     'description': a['description'] or '', 'issued_date': _safe_str(a['issued_date']),
                     'effective_date': _safe_str(a['effective_date']),
                     'expiry_date': _safe_str(a['expiry_date']), 'status': a['status'] or 'Pending',
                     'supporting_document': a['supporting_document'] or ''}
                    for i, a in enumerate(actions)
                ],
            })
            appeals = models.DisciplinaryAppeal.objects.filter(action__case=case, is_active=True).select_related('decided_by')
            for ap in appeals:
                db.collection('hrm_disciplinary_appeals').document(str(ap.id)).set({
                    'action_id': str(ap.action_id),
                    'case_number': case.case_number,
                    'employee_name': case.employee.name if case.employee else '',
                    'appeal_date': _safe_str(ap.appeal_date),
                    'grounds': ap.grounds,
                    'supporting_evidence': ap.supporting_evidence or '',
                    'status': ap.status,
                    'decision_date': _safe_str(ap.decision_date),
                    'decision_notes': ap.decision_notes or '',
                    'decided_by': _user_ref(ap.decided_by),
                    'is_active': ap.is_active,
                    'created_at': ap.created_at.isoformat() if ap.created_at else None,
                    'updated_at': ap.updated_at.isoformat() if ap.updated_at else None,
                })
            migrated += 1
        # Counter
        last = models.DisciplinaryCase.objects.order_by('-case_number').values_list('case_number', flat=True).first()
        if last:
            seq = int(last.split('-')[-1])
            db.collection('hrm_counters').document('disciplinary').set({'sequence': seq})
        self.stdout.write(f'  → {migrated} cases')

        # ── 2. Employee Education ────────────────────────────────────────
        self.stdout.write('Migrating Education...')
        cnt = 0
        for obj in models.EmployeeEducation.objects.filter(is_active=True).select_related('employee'):
            db.collection('hrm_employee_education').document(str(obj.id)).set({
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'degree': obj.degree,
                'institution': obj.institution,
                'field_of_study': obj.field_of_study or '',
                'start_year': obj.start_year,
                'end_year': obj.end_year,
                'grade': obj.grade or '',
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} records')

        # ── 3. Employee Experience ───────────────────────────────────────
        self.stdout.write('Migrating Experience...')
        cnt = 0
        for obj in models.EmployeeExperience.objects.filter(is_active=True).select_related('employee'):
            db.collection('hrm_employee_experience').document(str(obj.id)).set({
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'company': obj.company,
                'job_title': obj.job_title,
                'start_date': _safe_str(obj.start_date),
                'end_date': _safe_str(obj.end_date),
                'is_current': obj.is_current,
                'description': obj.description or '',
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} records')

        # ── 4. Employee Skill ────────────────────────────────────────────
        self.stdout.write('Migrating Skills...')
        cnt = 0
        for obj in models.EmployeeSkill.objects.filter(is_active=True).select_related('employee'):
            db.collection('hrm_employee_skills').document(str(obj.id)).set({
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'skill_name': obj.skill_name,
                'proficiency': obj.proficiency,
                'years_of_experience': float(obj.years_of_experience) if obj.years_of_experience else None,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} records')

        # ── 5. Competency ────────────────────────────────────────────────
        self.stdout.write('Migrating Competencies...')
        cnt = 0
        for obj in models.Competency.objects.filter(is_active=True):
            db.collection('hrm_competencies').document(str(obj.id)).set({
                'name': obj.name,
                'category': obj.category,
                'description': obj.description or '',
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} records')

        # ── 6. Competency Rating ─────────────────────────────────────────
        self.stdout.write('Migrating Competency Ratings...')
        cnt = 0
        for obj in models.CompetencyRating.objects.filter(is_active=True).select_related('employee', 'competency'):
            db.collection('hrm_competency_ratings').document(str(obj.id)).set({
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'competency': f'hrm_competencies/{obj.competency_id}',
                'competency_name': obj.competency.name if obj.competency else '',
                'rating': obj.rating,
                'assessed_by': _user_ref(obj.assessed_by),
                'assessment_date': _safe_str(obj.assessment_date),
                'notes': obj.notes or '',
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} records')

        # ── 7. Feedback ──────────────────────────────────────────────────
        self.stdout.write('Migrating Feedback...')
        cnt = 0
        for obj in models.FeedbackQuestion.objects.filter(is_active=True):
            db.collection('hrm_feedback_questions').document(str(obj.id)).set({
                'category': obj.category,
                'question_text': obj.question_text,
                'is_required': obj.is_required,
                'order': obj.order,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} questions')
        cnt = 0
        for obj in models.FeedbackRequest.objects.filter(is_active=True).select_related('reviewee'):
            db.collection('hrm_feedback_requests').document(str(obj.id)).set({
                'reviewer': _user_ref(obj.reviewer),
                'reviewee': f'hrm_employees/{obj.reviewee.firestore_id}' if obj.reviewee and obj.reviewee.firestore_id else None,
                'reviewee_name': obj.reviewee.name if obj.reviewee else '',
                'review_cycle_id': str(obj.review_cycle_id) if obj.review_cycle_id else None,
                'relationship': obj.relationship or '',
                'status': obj.status,
                'due_date': _safe_str(obj.due_date),
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} requests')
        cnt = 0
        for obj in models.FeedbackResponse.objects.select_related('request', 'question'):
            db.collection('hrm_feedback_responses').document(str(obj.id)).set({
                'request': str(obj.request_id),
                'question': str(obj.question_id),
                'rating': obj.rating,
                'response_text': obj.response_text or '',
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} responses')

        # ── 8. Surveys ───────────────────────────────────────────────────
        self.stdout.write('Migrating Surveys...')
        cnt = 0
        for obj in models.EngagementSurvey.objects.filter(is_active=True):
            db.collection('hrm_surveys').document(str(obj.id)).set({
                'title': obj.title,
                'description': obj.description or '',
                'start_date': _safe_str(obj.start_date),
                'end_date': _safe_str(obj.end_date),
                'is_anonymous': obj.is_anonymous,
                'status': obj.status,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
                'created_by': _user_ref(obj.created_by),
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} surveys')
        cnt = 0
        for obj in models.SurveyQuestion.objects.filter(is_active=True).select_related('survey'):
            db.collection('hrm_survey_questions').document(str(obj.id)).set({
                'survey': str(obj.survey_id),
                'survey_title': obj.survey.title if obj.survey else '',
                'question_text': obj.question_text,
                'question_type': obj.question_type,
                'options_json': obj.options_json or [],
                'order': obj.order,
                'is_required': obj.is_required,
                'is_active': obj.is_active,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} questions')
        cnt = 0
        for obj in models.SurveyResponse.objects.select_related('employee'):
            db.collection('hrm_survey_responses').document(str(obj.id)).set({
                'survey': str(obj.survey_id),
                'question': str(obj.question_id),
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else None,
                'response_text': obj.response_text or '',
                'response_value': obj.response_value,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} responses')

        # ── 9. Compliance Reminders ──────────────────────────────────────
        self.stdout.write('Migrating Compliance Reminders...')
        cnt = 0
        for obj in models.ComplianceReminder.objects.filter(is_active=True).select_related('employee'):
            db.collection('hrm_compliance_reminders').document(str(obj.id)).set({
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'reminder_type': obj.reminder_type,
                'title': obj.title,
                'description': obj.description or '',
                'due_date': _safe_str(obj.due_date),
                'completed_date': _safe_str(obj.completed_date),
                'status': obj.status,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} reminders')

        # ── 10. Talent Review ────────────────────────────────────────────
        self.stdout.write('Migrating Talent Review...')
        cnt = 0
        for obj in models.TalentReviewMeeting.objects.filter(is_active=True):
            db.collection('hrm_talent_review_meetings').document(str(obj.id)).set({
                'title': obj.title,
                'meeting_date': _safe_str(obj.meeting_date),
                'notes': obj.notes or '',
                'status': obj.status,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
                'created_by': _user_ref(obj.created_by),
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} meetings')
        cnt = 0
        for obj in models.NineBoxCell.objects.filter(is_active=True).select_related('employee'):
            db.collection('hrm_nine_box_cells').document(str(obj.id)).set({
                'talent_review': str(obj.talent_review_id),
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'performance': obj.performance,
                'potential': obj.potential,
                'notes': obj.notes or '',
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} cells')

        # ── 11. Notifications ────────────────────────────────────────────
        self.stdout.write('Migrating Notifications...')
        cnt = 0
        for obj in models.Notification.objects.filter(is_active=True):
            db.collection('hrm_notifications').document(str(obj.id)).set({
                'recipient': _user_ref(obj.recipient),
                'title': obj.title,
                'message': obj.message,
                'channel': obj.channel,
                'notification_type': obj.notification_type or '',
                'link': obj.link or '',
                'is_read': obj.is_read,
                'read_at': _safe_str(obj.read_at),
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} notifications')
        cnt = 0
        for obj in models.NotificationPreference.objects.all():
            db.collection('hrm_notification_preferences').document(str(obj.id)).set({
                'user': _user_ref(obj.user),
                'notify_in_app': obj.notify_in_app,
                'notify_email': obj.notify_email,
                'notify_push': obj.notify_push,
                'digest_frequency': obj.digest_frequency,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} prefs')
        cnt = 0
        for obj in models.DeviceToken.objects.filter(is_active=True):
            db.collection('hrm_device_tokens').document(str(obj.id)).set({
                'user': _user_ref(obj.user),
                'fcm_token': obj.fcm_token,
                'platform': obj.platform or '',
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} tokens')

        # ── 12. HRM Settings ─────────────────────────────────────────────
        self.stdout.write('Migrating HRM Settings...')
        cnt = 0
        for obj in models.HRMSetting.objects.filter(is_active=True):
            db.collection('hrm_settings').document(str(obj.id)).set({
                'key': obj.key,
                'value': obj.value,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} settings')

        # ── 13. Candidate Documents ──────────────────────────────────────
        self.stdout.write('Migrating Candidate Documents...')
        cnt = 0
        for obj in models.CandidateDocument.objects.select_related('candidate'):
            db.collection('hrm_candidate_documents').document(str(obj.id)).set({
                'candidate': str(obj.candidate_id),
                'document_type': obj.document_type,
                'file_url': obj.file.url if obj.file else None,
                'uploaded_at': _safe_str(obj.uploaded_at),
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} documents')

        # ── 14. Payroll Employees ────────────────────────────────────────
        self.stdout.write('Migrating Payroll Employees...')
        cnt = 0
        for obj in models.PayrollEmployee.objects.select_related('payroll', 'employee'):
            db.collection('hrm_payroll_employees').document(str(obj.id)).set({
                'payroll': str(obj.payroll_id),
                'payroll_period': obj.payroll.period if obj.payroll else '',
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'basic_salary': float(obj.basic_salary),
                'house_rent': float(obj.house_rent),
                'medical_allowance': float(obj.medical_allowance),
                'conveyance_allowance': float(obj.conveyance_allowance),
                'utility': float(obj.utility),
                'mobile_bill': float(obj.mobile_bill),
                'gross_pay': float(obj.gross_pay),
                'deductions': float(obj.deductions),
                'net_pay': float(obj.net_pay),
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} records')

        # ── 15. Dual-persistence models (add Firestore where ORM-only) ──
        self.stdout.write('Migrating Rating Templates & Scales...')
        cnt = 0
        for obj in models.RatingTemplate.objects.filter(is_active=True):
            scales = list(models.RatingScale.objects.filter(template=obj, is_active=True).values(
                'label', 'value', 'definition', 'order'
            ))
            db.collection('hrm_rating_templates').document(str(obj.id)).set({
                'name': obj.name,
                'description': obj.description or '',
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
                'scales': [
                    {'label': s['label'], 'value': float(s['value']),
                     'definition': s['definition'] or '', 'order': s['order']}
                    for s in scales
                ],
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} templates')

        self.stdout.write('Migrating Leave Policies & Balances...')
        cnt = 0
        for obj in models.LeavePolicy.objects.filter(is_active=True):
            db.collection('hrm_leave_policies').document(str(obj.id)).set({
                'employee_type': obj.employee_type,
                'leave_type': obj.leave_type,
                'entitled_days': float(obj.entitled_days),
                'carry_forward_days': float(obj.carry_forward_days),
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} policies')
        cnt = 0
        for obj in models.LeaveBalance.objects.filter(is_active=True).select_related('employee'):
            db.collection('hrm_leave_balances').document(str(obj.id)).set({
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'leave_type': obj.leave_type,
                'entitled': float(obj.entitled),
                'used': float(obj.used),
                'pending': float(obj.pending),
                'available': float(obj.available),
                'period': obj.period,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} balances')

        self.stdout.write('Migrating Employee KPIs, PIPs & Milestones...')
        cnt = 0
        for obj in models.EmployeeKPI.objects.filter(is_active=True).select_related('employee', 'kpi'):
            db.collection('hrm_employee_kpis').document(str(obj.id)).set({
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'review_cycle': str(obj.review_cycle_id),
                'kpi': str(obj.kpi_id),
                'kpi_name': obj.kpi.name if obj.kpi else '',
                'target_value': float(obj.target_value) if obj.target_value else None,
                'actual_value': float(obj.actual_value) if obj.actual_value else None,
                'weight': float(obj.weight),
                'score': float(obj.score) if obj.score else None,
                'comments': obj.comments or '',
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} employee KPIs')

        self.stdout.write('Migrating Training Needs, Dev Plans & Nominations...')
        cnt = 0
        for obj in models.TrainingNeed.objects.filter(is_active=True).select_related('employee'):
            db.collection('hrm_training_needs').document(str(obj.id)).set({
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'skill_gap': obj.skill_gap,
                'recommended_training': obj.recommended_training or '',
                'priority': obj.priority,
                'status': obj.status,
                'notes': obj.notes or '',
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
                'created_by': _user_ref(obj.created_by),
                'updated_by': _user_ref(obj.updated_by),
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} training needs')
        cnt = 0
        for obj in models.DevelopmentPlan.objects.filter(is_active=True).select_related('employee'):
            db.collection('hrm_development_plans').document(str(obj.id)).set({
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'title': obj.title,
                'description': obj.description or '',
                'goals': obj.goals or '',
                'start_date': _safe_str(obj.start_date),
                'target_end_date': _safe_str(obj.target_end_date),
                'completed_date': _safe_str(obj.completed_date),
                'status': obj.status,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
                'created_by': _user_ref(obj.created_by),
                'updated_by': _user_ref(obj.updated_by),
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} dev plans')
        cnt = 0
        for obj in models.TrainingNomination.objects.filter(is_active=True).select_related('employee'):
            db.collection('hrm_training_nominations').document(str(obj.id)).set({
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'course_name': obj.course_name,
                'provider': obj.provider or '',
                'start_date': _safe_str(obj.start_date),
                'end_date': _safe_str(obj.end_date),
                'cost': float(obj.cost) if obj.cost else None,
                'status': obj.status,
                'certificate_issued': obj.certificate_issued,
                'notes': obj.notes or '',
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
                'created_by': _user_ref(obj.created_by),
                'updated_by': _user_ref(obj.updated_by),
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} nominations')

        self.stdout.write('Migrating Succession models...')
        cnt = 0
        for obj in models.KeyPosition.objects.filter(is_active=True).select_related('department'):
            db.collection('hrm_key_positions').document(str(obj.id)).set({
                'position_title': obj.position_title,
                'position_id': str(obj.position_id) if obj.position_id else None,
                'department': str(obj.department_id) if obj.department_id else None,
                'department_name': obj.department.name if obj.department else '',
                'incumbent': f'hrm_employees/{obj.incumbent.firestore_id}' if obj.incumbent and obj.incumbent.firestore_id else None,
                'incumbent_name': obj.incumbent.name if obj.incumbent else None,
                'risk_of_vacancy': obj.risk_of_vacancy,
                'readiness_gap': obj.readiness_gap or '',
                'status': obj.status,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} key positions')
        cnt = 0
        for obj in models.SuccessorCandidate.objects.filter(is_active=True).select_related('employee', 'key_position'):
            db.collection('hrm_successor_candidates').document(str(obj.id)).set({
                'key_position': str(obj.key_position_id),
                'position_title': obj.key_position.position_title if obj.key_position else '',
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'readiness': obj.readiness,
                'strengths': obj.strengths or '',
                'development_needs': obj.development_needs or '',
                'notes': obj.notes or '',
                'is_primary': obj.is_primary,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} successors')
        cnt = 0
        for obj in models.SuccessionPlan.objects.filter(is_active=True).select_related('department'):
            db.collection('hrm_succession_plans').document(str(obj.id)).set({
                'title': obj.title,
                'description': obj.description or '',
                'department': str(obj.department_id) if obj.department_id else None,
                'department_name': obj.department.name if obj.department else '',
                'review_date': _safe_str(obj.review_date),
                'status': obj.status,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} plans')

        self.stdout.write('Migrating Performance (PIP milestones)...')
        cnt = 0
        for obj in models.PIPMilestone.objects.filter(is_active=True).select_related('pip'):
            db.collection('hrm_pip_milestones').document(str(obj.id)).set({
                'pip': str(obj.pip_id),
                'employee_name': obj.pip.employee.name if obj.pip and obj.pip.employee else '',
                'description': obj.description,
                'due_date': _safe_str(obj.due_date),
                'status': obj.status,
                'notes': obj.notes or '',
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} milestones')
        # Also migrate PerformanceImprovementPlans that exist in Firestore pattern
        cnt = 0
        for obj in models.PerformanceImprovementPlan.objects.filter(is_active=True).select_related('employee'):
            milestones = list(models.PIPMilestone.objects.filter(pip=obj, is_active=True).values(
                'description', 'due_date', 'status', 'notes'
            ))
            db.collection('hrm_performance_improvement_plans').document(str(obj.id)).set({
                'employee': f'hrm_employees/{obj.employee.firestore_id}' if obj.employee and obj.employee.firestore_id else None,
                'employee_name': obj.employee.name if obj.employee else '',
                'review_id': str(obj.review_id) if obj.review_id else None,
                'issue_description': obj.issue_description,
                'improvement_goals': obj.improvement_goals,
                'start_date': _safe_str(obj.start_date),
                'end_date': _safe_str(obj.end_date),
                'status': obj.status,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
                'milestones': [
                    {'description': m['description'], 'due_date': _safe_str(m['due_date']),
                     'status': m['status'], 'notes': m['notes'] or ''}
                    for m in milestones
                ],
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} PIPs')

        self.stdout.write('Migrating Review Cycles & KPI definitions...')
        cnt = 0
        for obj in models.ReviewCycle.objects.filter(is_active=True):
            db.collection('hrm_review_cycles').document(str(obj.id)).set({
                'name': obj.name,
                'start_date': _safe_str(obj.start_date),
                'end_date': _safe_str(obj.end_date),
                'review_type': obj.review_type,
                'status': obj.status,
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
                'created_by': _user_ref(obj.created_by),
                'updated_by': _user_ref(obj.updated_by),
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} review cycles')
        cnt = 0
        for obj in models.KPI.objects.filter(is_active=True):
            db.collection('hrm_kpis').document(str(obj.id)).set({
                'name': obj.name,
                'description': obj.description or '',
                'unit': obj.unit or '',
                'target_value': float(obj.target_value) if obj.target_value else None,
                'default_weight': float(obj.default_weight),
                'is_active': obj.is_active,
                'created_at': obj.created_at.isoformat() if obj.created_at else None,
                'updated_at': obj.updated_at.isoformat() if obj.updated_at else None,
            })
            cnt += 1
        self.stdout.write(f'  → {cnt} KPI definitions')

        self.stdout.write(self.style.SUCCESS('Migration complete!'))
