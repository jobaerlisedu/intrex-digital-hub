from rest_framework import serializers
from .. import models


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Department
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Position
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeSerializer(serializers.ModelSerializer):
    name = serializers.ReadOnlyField()

    class Meta:
        model = models.Employee
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecruitmentCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RecruitmentCandidate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecruitmentShortlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RecruitmentShortlist
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecruitmentInterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RecruitmentInterview
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecruitmentSelectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RecruitmentSelection
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AttendanceSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = models.Attendance
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeaveSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = models.Leave
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Holiday
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AdvanceSalarySerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = models.AdvanceSalary
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Payroll
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PayrollEmployeeSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = models.PayrollEmployee
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class EmployeeShiftSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = models.EmployeeShift
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class OnboardingTaskSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = models.OnboardingTask
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ExitClearanceSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = models.ExitClearance
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class ExpenseClaimSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = models.ExpenseClaim
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = models.Document
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class AssetSerializer(serializers.ModelSerializer):
    employee = EmployeeSerializer(read_only=True)

    class Meta:
        model = models.Asset
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class HRMSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.HRMSetting
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Performance Management ─────────────────────────────────────────────

class ReviewCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ReviewCycle
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class RatingTemplateSerializer(serializers.ModelSerializer):
    scales = serializers.SerializerMethodField()

    class Meta:
        model = models.RatingTemplate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_scales(self, obj):
        return RatingScaleSerializer(obj.scales.filter(is_active=True), many=True).data


class RatingScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.RatingScale
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class KPISerializer(serializers.ModelSerializer):
    class Meta:
        model = models.KPI
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeKPISerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.name')
    kpi_name = serializers.ReadOnlyField(source='kpi.name')
    cycle_name = serializers.ReadOnlyField(source='review_cycle.name')

    class Meta:
        model = models.EmployeeKPI
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PerformanceReviewSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.name')
    reviewer_name = serializers.ReadOnlyField(source='reviewer.name')
    cycle_name = serializers.ReadOnlyField(source='review_cycle.name')

    class Meta:
        model = models.PerformanceReview
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PIPMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PIPMilestone
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PerformanceImprovementPlanSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.name')
    milestones = PIPMilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = models.PerformanceImprovementPlan
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Leave Balance ──────────────────────────────────────────────────────

class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LeavePolicy
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.name')

    class Meta:
        model = models.LeaveBalance
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'available']


# ── Training & Development ─────────────────────────────────────────────

class TrainingNeedSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.name')

    class Meta:
        model = models.TrainingNeed
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DevelopmentPlanSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.name')

    class Meta:
        model = models.DevelopmentPlan
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class TrainingNominationSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.name')

    class Meta:
        model = models.TrainingNomination
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Notifications ─────────────────────────────────────────────────────

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Notification
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'read_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NotificationPreference
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DeviceToken
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Succession Planning ────────────────────────────────────────────────

class KeyPositionSerializer(serializers.ModelSerializer):
    position_title_display = serializers.ReadOnlyField(source='position.title')
    department_name = serializers.ReadOnlyField(source='department.name')
    incumbent_name = serializers.ReadOnlyField(source='incumbent.name')

    class Meta:
        model = models.KeyPosition
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SuccessorCandidateSerializer(serializers.ModelSerializer):
    employee_name = serializers.ReadOnlyField(source='employee.name')

    class Meta:
        model = models.SuccessorCandidate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SuccessionPlanSerializer(serializers.ModelSerializer):
    department_name = serializers.ReadOnlyField(source='department.name')

    class Meta:
        model = models.SuccessionPlan
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Employee Skills & Education ──────────────────────────────────────────

class EmployeeEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmployeeEducation
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmployeeExperience
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmployeeSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EmployeeSkill
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompetencySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Competency
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompetencyRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CompetencyRating
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class CandidateDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.CandidateDocument
        fields = '__all__'
        read_only_fields = ['id', 'uploaded_at']


# ── 360 Feedback ─────────────────────────────────────────────────────────

class FeedbackQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FeedbackQuestion
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


class FeedbackRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FeedbackRequest
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class FeedbackResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.FeedbackResponse
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


# ── Engagement Surveys ───────────────────────────────────────────────────

class EngagementSurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EngagementSurvey
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class SurveyQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SurveyQuestion
        fields = '__all__'
        read_only_fields = ['id']


class SurveyResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SurveyResponse
        fields = '__all__'
        read_only_fields = ['id', 'created_at']


# ── Compliance Calendar ──────────────────────────────────────────────────

class ComplianceReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ComplianceReminder
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


# ── Talent Review & 9-Box ────────────────────────────────────────────────

class TalentReviewMeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.TalentReviewMeeting
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class NineBoxCellSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.NineBoxCell
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
