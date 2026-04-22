from rest_framework import serializers

from .models import TextSubmission


class TextSubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)

    class Meta:
        model = TextSubmission
        fields = [
            'id', 'student', 'student_name', 'classroom', 'title',
            'content', 'language', 'status', 'submitted_at', 'updated_at',
        ]
        read_only_fields = ['id', 'student', 'status', 'submitted_at', 'updated_at']


class TextSubmissionListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)

    class Meta:
        model = TextSubmission
        fields = [
            'id', 'student', 'student_name', 'classroom', 'title',
            'language', 'status', 'submitted_at',
        ]
