from rest_framework import serializers

from .models import DetectedError, CorrectionAttempt


class DetectedErrorSerializer(serializers.ModelSerializer):
    attempt_count = serializers.SerializerMethodField()

    class Meta:
        model = DetectedError
        fields = [
            'id', 'submission', 'error_category', 'severity',
            'start_offset', 'end_offset', 'original_text',
            'is_resolved', 'attempt_count', 'created_at',
        ]
        # hint_text and correct_solution intentionally excluded —
        # they are revealed progressively through the correction workflow

    def get_attempt_count(self, obj):
        return obj.attempts.count()


class DetectedErrorDetailSerializer(serializers.ModelSerializer):
    attempts = serializers.SerializerMethodField()

    class Meta:
        model = DetectedError
        fields = [
            'id', 'submission', 'error_category', 'severity',
            'start_offset', 'end_offset', 'original_text',
            'is_resolved', 'attempts', 'created_at',
            'spacy_pos_tag', 'error_context',
        ]

    def get_attempts(self, obj):
        return CorrectionAttemptSerializer(obj.attempts.all(), many=True).data


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
