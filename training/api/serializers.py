from rest_framework import serializers

from training.models import (
    Ambassador,
    Assessment,
    Batch,
    Certificate,
    ClassSession,
    Commission,
    Course,
    Expense,
    Inquiry,
    Institute,
    JobPlacement,
    Payment,
    Registration,
)


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class BatchSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Batch
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class AssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class RegistrationSerializer(serializers.ModelSerializer):
    payment = PaymentSerializer(read_only=True)
    assessment = AssessmentSerializer(read_only=True)
    certificates = CertificateSerializer(many=True, read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)
    batch_id_display = serializers.CharField(source='batch.batch_id', read_only=True)

    class Meta:
        model = Registration
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class InquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class InstituteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Institute
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class AmbassadorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ambassador
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class CommissionSerializer(serializers.ModelSerializer):
    agent_name_display = serializers.CharField(source='agent.name', read_only=True)

    class Meta:
        model = Commission
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class ClassSessionSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = ClassSession
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'updated_by']


class JobPlacementSerializer(serializers.ModelSerializer):
    student_name_display = serializers.CharField(source='registration.full_name', read_only=True)

    class Meta:
        model = JobPlacement
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']
