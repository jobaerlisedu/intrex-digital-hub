from rest_framework import serializers
from solutions.models import Project, ProjectPhase, Task, ProjectRequisition, SoftwareLicense, ProjectStakeholder, Meeting


class ProjectPhaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectPhase
        fields = '__all__'


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class ProjectRequisitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectRequisition
        fields = '__all__'


class SoftwareLicenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SoftwareLicense
        fields = '__all__'


class ProjectStakeholderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStakeholder
        fields = '__all__'


class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = '__all__'


class ProjectSerializer(serializers.ModelSerializer):
    phases = ProjectPhaseSerializer(many=True, read_only=True)
    stakeholders = ProjectStakeholderSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = '__all__'
