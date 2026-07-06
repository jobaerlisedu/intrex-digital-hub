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
