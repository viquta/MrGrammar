from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from classrooms.models import Classroom
from feedback.models import CorrectionAttempt, DetectedError
from feedback.services import CorrectionWorkflowService
from submissions.models import TextSubmission


MRGRAMMAR_TEST_SETTINGS = {
	'MAX_CORRECTION_ATTEMPTS': 2,
	'HINT_THRESHOLD': 1,
	'SUPPORTED_LANGUAGES': ['de'],
	'LANGUAGETOOL_URL': 'http://localhost:8010/v2',
	'SPACY_MODEL': 'de_core_news_md',
	'SPACY_SENTENCE_SPLIT': True,
	'ENABLE_LLM_EXPLANATIONS': True,
	'OLLAMA_BASE_URL': 'http://ollama.example.test:11434',
	'OLLAMA_MODEL': 'gemma4:26b',
	'OLLAMA_TIMEOUT_SECONDS': 5,
	'OLLAMA_EXPLANATION_TEMPERATURE': 0.2,
}


@override_settings(MRGRAMMAR=MRGRAMMAR_TEST_SETTINGS)
class CorrectionWorkflowServiceTests(TestCase):
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
			content='Der hund läuft.',
			language='de',
		)
		self.error = DetectedError.objects.create(
			submission=self.submission,
			error_category=DetectedError.Category.ARTICLE,
			severity=DetectedError.Severity.MEDIUM,
			start_offset=0,
			end_offset=3,
			original_text='Der',
			hint_text='Check the article that fits the noun.',
			correct_solution='Die',
			spacy_pos_tag='DET',
			error_context={'tokens': [{'text': 'Der', 'pos': 'DET'}]},
		)
		self.service = CorrectionWorkflowService()

	def test_first_failed_attempt_returns_hint_and_unlocks_manual_reveal(self):
		result = self.service.submit_attempt(self.error, self.student, 'Das')

		self.assertEqual(result['attempt_number'], 1)
		self.assertEqual(result['display_attempt_number'], 2)
		self.assertEqual(result['phase'], 'phase_2')
		self.assertEqual(result['outcome'], 'hint')
		self.assertEqual(result['hint'], self.error.hint_text)
		self.assertTrue(result['can_request_solution'])
		self.error.refresh_from_db()
		self.assertFalse(self.error.is_resolved)

	@patch('feedback.services.ExplanationGenerationService.generate', return_value='Use the feminine article with this noun.')
	def test_second_failed_attempt_reveals_solution_and_explanation(self, _mock_generate):
		self.service.submit_attempt(self.error, self.student, 'Das')

		result = self.service.submit_attempt(self.error, self.student, 'Dem')

		self.assertEqual(result['attempt_number'], 2)
		self.assertEqual(result['display_attempt_number'], 3)
		self.assertEqual(result['phase'], 'phase_3')
		self.assertEqual(result['outcome'], 'solution_revealed')
		self.assertEqual(result['solution'], self.error.correct_solution)
		self.assertEqual(result['explanation'], 'Use the feminine article with this noun.')
		self.assertFalse(result['can_request_solution'])
		self.error.refresh_from_db()
		self.assertTrue(self.error.is_resolved)

	def test_correct_answer_resolves_error(self):
		result = self.service.submit_attempt(self.error, self.student, 'Die')

		self.assertTrue(result['is_correct'])
		self.assertEqual(result['outcome'], 'correct')
		self.error.refresh_from_db()
		self.assertTrue(self.error.is_resolved)

	@patch('feedback.services.ExplanationGenerationService.generate', return_value='The article must agree with the noun.')
	def test_manual_reveal_returns_phase_three_payload(self, _mock_generate):
		self.service.submit_attempt(self.error, self.student, 'Das')

		result = self.service.request_solution(self.error, attempted_text='Das')

		self.assertEqual(result['phase'], 'phase_3')
		self.assertEqual(result['outcome'], 'manual_reveal')
		self.assertEqual(result['solution'], self.error.correct_solution)
		self.assertIn('explanation', result)


@override_settings(MRGRAMMAR=MRGRAMMAR_TEST_SETTINGS)
class FeedbackViewsTests(APITestCase):
	def setUp(self):
		user_model = get_user_model()
		self.student = user_model.objects.create_user(
			username='student1',
			password='testpass123',
			role='student',
		)
		self.other_student = user_model.objects.create_user(
			username='student2',
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
			content='Der hund läuft.',
			language='de',
		)
		self.error = DetectedError.objects.create(
			submission=self.submission,
			error_category=DetectedError.Category.VERB_TENSE,
			severity=DetectedError.Severity.MEDIUM,
			start_offset=9,
			end_offset=14,
			original_text='läuft',
			hint_text='Check the verb form.',
			correct_solution='läuft',
			spacy_pos_tag='VERB',
		)
		self.client.force_authenticate(user=self.student)

	def test_submission_errors_endpoint_returns_display_fields(self):
		url = reverse('submission-errors', kwargs={'submission_id': self.submission.id})

		response = self.client.get(url)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data[0]['display_group'], 'verb_phrase')
		self.assertEqual(response.data[0]['next_try_number'], 2)
		self.assertFalse(response.data[0]['can_request_solution'])

	def test_cannot_request_solution_before_first_failed_attempt(self):
		url = reverse('request-solution', kwargs={'pk': self.error.id})

		response = self.client.post(url, data={}, format='json')

		self.assertEqual(response.status_code, 400)
		self.assertEqual(response.data['detail'], 'Solution reveal is not available yet.')

	@patch('feedback.services.ExplanationGenerationService.generate', return_value='Review the conjugation.')
	def test_can_request_solution_after_first_failed_attempt(self, _mock_generate):
		submit_url = reverse('submit-attempt', kwargs={'pk': self.error.id})
		solution_url = reverse('request-solution', kwargs={'pk': self.error.id})

		submit_response = self.client.post(
			submit_url,
			data={'attempted_text': 'laufen'},
			format='json',
		)
		response = self.client.post(
			solution_url,
			data={'attempted_text': 'laufen'},
			format='json',
		)

		self.assertEqual(submit_response.status_code, 200)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['outcome'], 'manual_reveal')
		self.error.refresh_from_db()
		self.assertTrue(self.error.is_resolved)

	def test_student_cannot_access_another_students_error(self):
		self.client.force_authenticate(user=self.other_student)
		url = reverse('submit-attempt', kwargs={'pk': self.error.id})

		response = self.client.post(url, data={'attempted_text': 'laufen'}, format='json')

		self.assertEqual(response.status_code, 404)

	def test_attempt_submission_records_attempt(self):
		url = reverse('submit-attempt', kwargs={'pk': self.error.id})

		response = self.client.post(url, data={'attempted_text': 'laufen'}, format='json')

		self.assertEqual(response.status_code, 200)
		self.assertEqual(CorrectionAttempt.objects.filter(error=self.error).count(), 1)
