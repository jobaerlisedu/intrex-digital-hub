from django.contrib import admin
from . import models


@admin.register(models.Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'status', 'is_active', 'created_at']
    list_filter = ['status', 'is_active']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['parent']


@admin.register(models.Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'status', 'is_active']
    list_filter = ['status', 'is_active']
    search_fields = ['title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['department', 'sub_department']


class PayrollEmployeeInline(admin.TabularInline):
    model = models.PayrollEmployee
    extra = 1
    raw_id_fields = ['employee']


@admin.register(models.Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['emp_id', 'name', 'department', 'position', 'status', 'is_active']
    list_filter = ['status', 'employee_type', 'gender', 'department', 'is_active']
    search_fields = ['emp_id', 'first_name', 'last_name', 'email', 'phone']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['department', 'sub_department', 'position', 'created_by', 'updated_by']
    fieldsets = [
        ('Identification', {'fields': ['emp_id', 'first_name', 'last_name', 'email', 'phone', 'alt_phone', 'national_id']}),
        ('Employment', {'fields': ['employee_type', 'department', 'sub_department', 'position', 'additional_roles', 'joining_date', 'status', 'exit_date', 'exit_type', 'exit_reason']}),
        ('Salary', {'fields': ['basic_salary', 'house_rent', 'medical_allowance', 'conveyance_allowance', 'utility', 'mobile_bill', 'gross_salary']}),
        ('Bank Details', {'fields': ['account_holder', 'account_number', 'bank_name', 'branch_name']}),
        ('Personal', {'fields': ['dob', 'gender', 'marital_status', 'religion', 'city', 'zip']}),
        ('Emergency Contact', {'fields': ['ec_primary_name', 'ec_primary_relation', 'ec_primary_mobile', 'ec_secondary_name', 'ec_secondary_relation', 'ec_secondary_mobile']}),
        ('Metadata', {'fields': ['id', 'contact_id', 'firestore_id', 'is_active', 'created_by', 'updated_by', 'created_at', 'updated_at']}),
    ]


@admin.register(models.RecruitmentCandidate)
class RecruitmentCandidateAdmin(admin.ModelAdmin):
    list_display = ['cand_id', 'name', 'position', 'status', 'date_applied']
    list_filter = ['status']
    search_fields = ['name', 'cand_id', 'position']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.RecruitmentShortlist)
class RecruitmentShortlistAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['name', 'position']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.RecruitmentInterview)
class RecruitmentInterviewAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'interviewer', 'date_time', 'status']
    list_filter = ['status']
    search_fields = ['name', 'interviewer']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.RecruitmentSelection)
class RecruitmentSelectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'offer_status', 'offer_date']
    list_filter = ['offer_status']
    search_fields = ['name', 'position']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'check_in', 'check_out', 'status']
    list_filter = ['status', 'date']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.Leave)
class LeaveAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'from_date', 'to_date', 'duration', 'status']
    list_filter = ['status', 'leave_type']
    search_fields = ['employee__first_name', 'employee__last_name', 'reason']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ['holiday_name', 'from_date', 'to_date', 'holiday_type']
    list_filter = ['holiday_type']
    search_fields = ['holiday_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.AdvanceSalary)
class AdvanceSalaryAdmin(admin.ModelAdmin):
    list_display = ['employee', 'amount', 'deduct_month', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['period', 'employee_count', 'total_net_pay', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['period']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [PayrollEmployeeInline]


@admin.register(models.PayrollEmployee)
class PayrollEmployeeAdmin(admin.ModelAdmin):
    list_display = ['payroll', 'employee', 'gross_pay', 'net_pay']
    list_filter = ['payroll__period']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['payroll', 'employee']


@admin.register(models.EmployeeShift)
class EmployeeShiftAdmin(admin.ModelAdmin):
    list_display = ['employee', 'shift_name', 'start_date', 'end_date']
    search_fields = ['employee__first_name', 'employee__last_name', 'shift_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.OnboardingTask)
class OnboardingTaskAdmin(admin.ModelAdmin):
    list_display = ['employee', 'task_name', 'due_date', 'status']
    list_filter = ['status']
    search_fields = ['employee__first_name', 'employee__last_name', 'task_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.ExitClearance)
class ExitClearanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'exit_date', 'it_clearance', 'finance_clearance', 'hr_clearance', 'status']
    list_filter = ['status', 'it_clearance', 'finance_clearance', 'hr_clearance']
    search_fields = ['employee__first_name', 'employee__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.ExpenseClaim)
class ExpenseClaimAdmin(admin.ModelAdmin):
    list_display = ['employee', 'category', 'amount', 'status', 'created_at']
    list_filter = ['status', 'category']
    search_fields = ['employee__first_name', 'employee__last_name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'document_type', 'document_number', 'expiry_date']
    list_filter = ['document_type']
    search_fields = ['employee__first_name', 'employee__last_name', 'document_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['asset_name', 'asset_tag', 'employee', 'status']
    list_filter = ['status']
    search_fields = ['asset_name', 'asset_tag', 'serial_number']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.HRMSetting)
class HRMSettingAdmin(admin.ModelAdmin):
    list_display = ['key', 'is_active']
    search_fields = ['key']
    readonly_fields = ['id', 'created_at', 'updated_at']


# ── Phase 2: Performance Management ───────────────────────────────

@admin.register(models.ReviewCycle)
class ReviewCycleAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'review_type', 'status']
    list_filter = ['review_type', 'status']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.RatingTemplate)
class RatingTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.RatingScale)
class RatingScaleAdmin(admin.ModelAdmin):
    list_display = ['label', 'value', 'template', 'order']
    list_filter = ['template']
    search_fields = ['label']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.KPI)
class KPIAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'target_value', 'default_weight']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.EmployeeKPI)
class EmployeeKPIAdmin(admin.ModelAdmin):
    list_display = ['employee', 'kpi', 'review_cycle', 'target_value', 'actual_value', 'score']
    list_filter = ['review_cycle']
    search_fields = ['employee__first_name', 'kpi__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee', 'review_cycle', 'kpi']


@admin.register(models.PerformanceReview)
class PerformanceReviewAdmin(admin.ModelAdmin):
    list_display = ['employee', 'reviewer', 'review_cycle', 'overall_score', 'status']
    list_filter = ['status', 'review_cycle']
    search_fields = ['employee__first_name', 'reviewer__first_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee', 'reviewer', 'review_cycle', 'rating_template', 'rating']


@admin.register(models.PerformanceImprovementPlan)
class PerformanceImprovementPlanAdmin(admin.ModelAdmin):
    list_display = ['employee', 'start_date', 'end_date', 'status']
    list_filter = ['status']
    search_fields = ['employee__first_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee', 'review']


@admin.register(models.PIPMilestone)
class PIPMilestoneAdmin(admin.ModelAdmin):
    list_display = ['pip', 'description', 'due_date', 'status']
    list_filter = ['status']
    search_fields = ['description']
    readonly_fields = ['id', 'created_at', 'updated_at']


# ── Phase 3: Leave Balance & Training ────────────────────────────

@admin.register(models.LeavePolicy)
class LeavePolicyAdmin(admin.ModelAdmin):
    list_display = ['employee_type', 'leave_type', 'entitled_days', 'carry_forward_days']
    list_filter = ['employee_type', 'leave_type']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'entitled', 'used', 'pending', 'available', 'period']
    list_filter = ['leave_type', 'period']
    search_fields = ['employee__first_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.TrainingNeed)
class TrainingNeedAdmin(admin.ModelAdmin):
    list_display = ['employee', 'skill_gap', 'recommended_training', 'priority', 'status']
    list_filter = ['priority', 'status']
    search_fields = ['employee__first_name', 'skill_gap']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.DevelopmentPlan)
class DevelopmentPlanAdmin(admin.ModelAdmin):
    list_display = ['employee', 'title', 'start_date', 'target_end_date', 'status']
    list_filter = ['status']
    search_fields = ['employee__first_name', 'title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.TrainingNomination)
class TrainingNominationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'course_name', 'provider', 'start_date', 'status', 'certificate_issued']
    list_filter = ['status']
    search_fields = ['employee__first_name', 'course_name', 'provider']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


# ── Phase 4: Notifications & Succession ──────────────────────────

@admin.register(models.Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'title', 'channel', 'notification_type', 'is_read', 'created_at']
    list_filter = ['channel', 'is_read', 'notification_type']
    search_fields = ['recipient__username', 'title', 'message']
    readonly_fields = ['id', 'created_at', 'updated_at', 'read_at']
    raw_id_fields = ['recipient']


@admin.register(models.NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'notify_in_app', 'notify_email', 'notify_push', 'digest_frequency']
    list_filter = ['notify_in_app', 'notify_email', 'digest_frequency']
    search_fields = ['user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'is_active', 'created_at']
    list_filter = ['platform', 'is_active']
    search_fields = ['user__username', 'fcm_token']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['user']


@admin.register(models.KeyPosition)
class KeyPositionAdmin(admin.ModelAdmin):
    list_display = ['position_title', 'department', 'risk_of_vacancy', 'status', 'is_active']
    list_filter = ['risk_of_vacancy', 'status', 'is_active']
    search_fields = ['position_title', 'readiness_gap']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['position', 'department', 'incumbent']


@admin.register(models.SuccessorCandidate)
class SuccessorCandidateAdmin(admin.ModelAdmin):
    list_display = ['employee', 'key_position', 'readiness', 'is_primary', 'is_active']
    list_filter = ['readiness', 'is_primary', 'is_active']
    search_fields = ['employee__first_name', 'key_position__position_title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['key_position', 'employee']


@admin.register(models.SuccessionPlan)
class SuccessionPlanAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'review_date', 'status', 'is_active']
    list_filter = ['status', 'is_active']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['department']


# ── Phase 5: Skills, Education, Experience ────────────────────────

@admin.register(models.EmployeeEducation)
class EmployeeEducationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'degree', 'institution', 'end_year', 'grade']
    list_filter = ['degree']
    search_fields = ['employee__first_name', 'institution', 'degree']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.EmployeeExperience)
class EmployeeExperienceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'job_title', 'company', 'start_date', 'end_date', 'is_current']
    list_filter = ['is_current']
    search_fields = ['employee__first_name', 'company', 'job_title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.EmployeeSkill)
class EmployeeSkillAdmin(admin.ModelAdmin):
    list_display = ['employee', 'skill_name', 'proficiency', 'years_of_experience']
    list_filter = ['proficiency']
    search_fields = ['employee__first_name', 'skill_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


@admin.register(models.Competency)
class CompetencyAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.CompetencyRating)
class CompetencyRatingAdmin(admin.ModelAdmin):
    list_display = ['employee', 'competency', 'rating', 'assessed_by', 'assessment_date']
    list_filter = ['rating']
    search_fields = ['employee__first_name', 'competency__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee', 'competency', 'assessed_by']


@admin.register(models.CandidateDocument)
class CandidateDocumentAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'document_type', 'uploaded_at']
    list_filter = ['document_type']
    search_fields = ['candidate__name']
    readonly_fields = ['id', 'uploaded_at']
    raw_id_fields = ['candidate']


# ── Phase 5: 360 Feedback ─────────────────────────────────────────

@admin.register(models.FeedbackQuestion)
class FeedbackQuestionAdmin(admin.ModelAdmin):
    list_display = ['category', 'question_text', 'is_required', 'order']
    list_filter = ['category']
    search_fields = ['question_text']
    readonly_fields = ['id', 'created_at']


@admin.register(models.FeedbackRequest)
class FeedbackRequestAdmin(admin.ModelAdmin):
    list_display = ['reviewer', 'reviewee', 'review_cycle', 'relationship', 'status', 'due_date']
    list_filter = ['status', 'relationship']
    search_fields = ['reviewer__username', 'reviewee__first_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['reviewer', 'reviewee', 'review_cycle']


@admin.register(models.FeedbackResponse)
class FeedbackResponseAdmin(admin.ModelAdmin):
    list_display = ['request', 'question', 'rating']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['request', 'question']


# ── Phase 5: Engagement Surveys ───────────────────────────────────

@admin.register(models.EngagementSurvey)
class EngagementSurveyAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'end_date', 'is_anonymous', 'status']
    list_filter = ['status', 'is_anonymous']
    search_fields = ['title']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.SurveyQuestion)
class SurveyQuestionAdmin(admin.ModelAdmin):
    list_display = ['survey', 'question_type', 'question_text', 'order', 'is_required']
    list_filter = ['question_type']
    search_fields = ['question_text']
    readonly_fields = ['id']
    raw_id_fields = ['survey']


@admin.register(models.SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    list_display = ['survey', 'question', 'employee', 'response_value', 'created_at']
    readonly_fields = ['id', 'created_at']
    raw_id_fields = ['survey', 'question', 'employee']


# ── Phase 5: Compliance Calendar ──────────────────────────────────

@admin.register(models.ComplianceReminder)
class ComplianceReminderAdmin(admin.ModelAdmin):
    list_display = ['employee', 'reminder_type', 'title', 'due_date', 'status']
    list_filter = ['reminder_type', 'status']
    search_fields = ['employee__first_name', 'title']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee']


# ── Phase 5: Talent Review & 9-Box ────────────────────────────────

@admin.register(models.TalentReviewMeeting)
class TalentReviewMeetingAdmin(admin.ModelAdmin):
    list_display = ['title', 'meeting_date', 'status']
    list_filter = ['status']
    search_fields = ['title']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(models.NineBoxCell)
class NineBoxCellAdmin(admin.ModelAdmin):
    list_display = ['employee', 'talent_review', 'performance', 'potential']
    list_filter = ['performance', 'potential']
    search_fields = ['employee__first_name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['employee', 'talent_review']
