from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Classroom, ClassroomMembership

User = get_user_model()


class ClassroomSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Classroom
        fields = ['id', 'name', 'language', 'created_by', 'created_at', 'student_count']
        read_only_fields = ['id', 'created_at', 'created_by']

    def get_student_count(self, obj):
        return obj.memberships.filter(role=ClassroomMembership.MemberRole.STUDENT).count()


class ClassroomMembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = ClassroomMembership
        fields = ['id', 'user', 'classroom', 'role', 'username', 'full_name', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class AddMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(choices=ClassroomMembership.MemberRole.choices)

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError('User not found.')
        return value
