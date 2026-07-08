from django.contrib.auth.models import User, Group
from rest_framework import serializers
from accounts.models import AuditLog, ActiveSession


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    group_names = serializers.ListField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'is_active', 'is_staff', 'is_superuser', 'date_joined',
                  'last_login', 'groups', 'group_names']
        read_only_fields = ['date_joined', 'last_login']

    def create(self, validated_data):
        group_names = validated_data.pop('group_names', [])
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        for name in group_names:
            group, _ = Group.objects.get_or_create(name=name)
            user.groups.add(group)
        return user

    def update(self, instance, validated_data):
        group_names = validated_data.pop('group_names', None)
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if group_names is not None:
            module_groups = Group.objects.filter(name__endswith='_access')
            instance.groups.remove(*module_groups)
            for name in group_names:
                group, _ = Group.objects.get_or_create(name=name)
                instance.groups.add(group)
        return instance


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default='')

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'username', 'action', 'module', 'description',
                  'ip_address', 'before_state', 'after_state', 'sha256_hash', 'timestamp']
        read_only_fields = ['sha256_hash', 'timestamp']


class ActiveSessionSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ActiveSession
        fields = ['id', 'user', 'username', 'ip_address', 'user_agent',
                  'created_at', 'last_activity']
        read_only_fields = ['created_at', 'last_activity']
