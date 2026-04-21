from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from classrooms.models import Classroom
from feedback.models import DetectedError
from submissions.models import TextSubmission


class AnalyzeSubmissionViewTests(APITestCase):
	def setUp(self):
		user_model = get_user_model()
		self.student = user_model.objects.create_user(
			username='student1',
			password='testpass123',
			role='student',
		)
		self.classroom = Classroom.objects.create(
			name='German A1',
			language='de',
			created_by=self.student,
		)
		self.submission = TextSubmission.objects.create(
			student=self.student,
			classroom=self.classroom,
			title='Mein Text',
			content='Ich bin ein Student.',
			language='de',
		)
		self.client.force_authenticate(user=self.student)

	@patch('nlp.views.ErrorDetectionService.analyze', side_effect=RuntimeError('boom'))
	def test_analyze_failure_resets_status_to_submitted(self, _mock_analyze):
		url = reverse('analyze-submission', kwargs={'submission_id': self.submission.id})

		response = self.client.post(url, data={}, format='json')

		self.submission.refresh_from_db()
		self.assertEqual(response.status_code, 502)
		self.assertEqual(self.submission.status, TextSubmission.Status.SUBMITTED)

	@patch(
		'nlp.services.LanguageToolClient.detect',
		return_value=[
			{'start_offset': 0, 'end_offset': 2, 'error_category': 'grammar', 'original_text': 'Ic', 'hint_text': 'h', 'correct_solution': 'Ich'},
			{'start_offset': 'bad', 'end_offset': 4, 'error_category': 'grammar'},
			{'start_offset': 3, 'end_offset': 2, 'error_category': 'grammar'},
		],
	)
	def test_analyze_ignores_malformed_errors_and_completes(self, _mock_detect):
		url = reverse('analyze-submission', kwargs={'submission_id': self.submission.id})

		response = self.client.post(url, data={}, format='json')

		self.submission.refresh_from_db()
		self.assertEqual(response.status_code, 200)
		self.assertEqual(self.submission.status, TextSubmission.Status.IN_REVIEW)
		self.assertEqual(DetectedError.objects.filter(submission=self.submission).count(), 1)
