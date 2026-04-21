from rest_framework import serializers
from django.conf import settings

from .models import DetectedError, CorrectionAttempt
from .presentation import derive_display_group, get_display_label


class DetectedErrorSerializer(serializers.ModelSerializer):
    attempt_count = serializers.SerializerMethodField()
    display_group = serializers.SerializerMethodField()
    display_label = serializers.SerializerMethodField()
    can_request_solution = serializers.SerializerMethodField()
    next_try_number = serializers.SerializerMethodField()

    class Meta:
        model = DetectedError
        fields = [
            'id', 'submission', 'error_category', 'severity',
            'start_offset', 'end_offset', 'original_text',
            'is_resolved', 'attempt_count', 'display_group',
            'display_label', 'can_request_solution', 'next_try_number',
            'created_at',
        ]
        # hint_text and correct_solution intentionally excluded —
        # they are revealed progressively through the correction workflow

    def get_attempt_count(self, obj):
        return obj.attempts.count()

    def get_display_group(self, obj):
        return derive_display_group(obj)

    def get_display_label(self, obj):
        return get_display_label(self.get_display_group(obj))

    def get_can_request_solution(self, obj):
        threshold = max(1, settings.MRGRAMMAR['HINT_THRESHOLD'])
        return not obj.is_resolved and obj.attempts.count() >= threshold

    def get_next_try_number(self, obj):
        return obj.attempts.count() + 2


class DetectedErrorDetailSerializer(serializers.ModelSerializer):
    attempts = serializers.SerializerMethodField()
    display_group = serializers.SerializerMethodField()
    display_label = serializers.SerializerMethodField()

    class Meta:
        model = DetectedError
        fields = [
            'id', 'submission', 'error_category', 'severity',
            'start_offset', 'end_offset', 'original_text',
            'is_resolved', 'attempts', 'created_at',
            'spacy_pos_tag', 'error_context',
            'display_group', 'display_label',
        ]

    def get_attempts(self, obj):
        return CorrectionAttemptSerializer(obj.attempts.all(), many=True).data

    def get_display_group(self, obj):
        return derive_display_group(obj)

    def get_display_label(self, obj):
        return get_display_label(self.get_display_group(obj))


class CorrectionAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectionAttempt
        fields = [
            'id', 'error', 'attempt_number', 'attempted_text',
            'is_correct', 'hint_shown', 'solution_shown', 'created_at',
        ]
        read_only_fields = [
            'id', 'attempt_number', 'is_correct',
            'hint_shown', 'solution_shown', 'created_at',
        ]


class SubmitAttemptSerializer(serializers.Serializer):
    attempted_text = serializers.CharField(max_length=1000)


class RequestSolutionSerializer(serializers.Serializer):
    attempted_text = serializers.CharField(max_length=1000, required=False, allow_blank=True)
