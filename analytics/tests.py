from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from analytics.models import LearnerErrorSummary
from classrooms.models import Classroom, ClassroomMembership
from feedback.models import CorrectionAttempt, DetectedError
from submissions.models import TextSubmission


MRGRAMMAR_TEST_SETTINGS = {
	'MAX_CORRECTION_ATTEMPTS': 2,
	'HINT_THRESHOLD': 1,
	'SUPPORTED_LANGUAGES': ['de'],
	'LANGUAGETOOL_URL': 'http://localhost:8010/v2',
	'SPACY_MODEL': 'de_core_news_md',
	'SPACY_SENTENCE_SPLIT': True,
	'ENABLE_LLM_EXPLANATIONS': False,
	'OLLAMA_BASE_URL': 'http://ollama.example.test:11434',
	'OLLAMA_MODEL': 'gemma4:26b',
	'OLLAMA_TIMEOUT_SECONDS': 5,
	'OLLAMA_EXPLANATION_TEMPERATURE': 0.2,
}


@override_settings(MRGRAMMAR=MRGRAMMAR_TEST_SETTINGS)
class AnalyticsViewsTests(APITestCase):
	def setUp(self):
		user_model = get_user_model()
		self.teacher = user_model.objects.create_user(
			username='teacher1',
			password='testpass123',
			role='teacher',
		)
		self.other_teacher = user_model.objects.create_user(
			username='teacher2',
			password='testpass123',
			role='teacher',
		)
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
		self.classmate = user_model.objects.create_user(
			username='student3',
			password='testpass123',
			role='student',
		)

		self.classroom = Classroom.objects.create(
			name='German A1',
			language='de',
			created_by=self.teacher,
		)
		self.other_classroom = Classroom.objects.create(
			name='German A2',
			language='de',
			created_by=self.other_teacher,
		)

		ClassroomMembership.objects.create(
			user=self.teacher,
			classroom=self.classroom,
			role=ClassroomMembership.MemberRole.TEACHER,
		)
		ClassroomMembership.objects.create(
			user=self.student,
			classroom=self.classroom,
			role=ClassroomMembership.MemberRole.STUDENT,
		)
		ClassroomMembership.objects.create(
			user=self.other_teacher,
			classroom=self.other_classroom,
			role=ClassroomMembership.MemberRole.TEACHER,
		)
		ClassroomMembership.objects.create(
			user=self.other_student,
			classroom=self.other_classroom,
			role=ClassroomMembership.MemberRole.STUDENT,
		)
		ClassroomMembership.objects.create(
			user=self.classmate,
			classroom=self.classroom,
			role=ClassroomMembership.MemberRole.STUDENT,
		)

		self.submission = TextSubmission.objects.create(
			student=self.student,
			classroom=self.classroom,
			title='Mein Text',
			content='Der hund läuft.',
			language='de',
		)
		self.other_submission = TextSubmission.objects.create(
			student=self.other_student,
			classroom=self.other_classroom,
			title='Anderer Text',
			content='Ich gehe nach Hause.',
			language='de',
		)
		self.second_submission = TextSubmission.objects.create(
			student=self.student,
			classroom=self.classroom,
			title='Zweiter Text',
			content='Ich gehe in der Schule.',
			language='de',
		)
		self.classmate_submission = TextSubmission.objects.create(
			student=self.classmate,
			classroom=self.classroom,
			title='Klassenarbeit',
			content='Wir gehen zu park.',
			language='de',
		)

		self.article_error = DetectedError.objects.create(
			submission=self.submission,
			error_category=DetectedError.Category.ARTICLE,
			severity=DetectedError.Severity.MEDIUM,
			start_offset=0,
			end_offset=3,
			original_text='Der',
			hint_text='Check the article.',
			correct_solution='Die',
			is_resolved=True,
			resolution_method=DetectedError.ResolutionMethod.CORRECT,
		)
		self.preposition_error = DetectedError.objects.create(
			submission=self.second_submission,
			error_category=DetectedError.Category.PREPOSITION,
			severity=DetectedError.Severity.MEDIUM,
			start_offset=9,
			end_offset=11,
			original_text='in',
			hint_text='Check the preposition.',
			correct_solution='in der',
			is_resolved=True,
			resolution_method=DetectedError.ResolutionMethod.MANUAL_REVEAL,
		)
		self.classmate_error = DetectedError.objects.create(
			submission=self.classmate_submission,
			error_category=DetectedError.Category.SPELLING,
			severity=DetectedError.Severity.MEDIUM,
			start_offset=13,
			end_offset=17,
			original_text='park',
			hint_text='Check the spelling.',
			correct_solution='Park',
			is_resolved=True,
			resolution_method=DetectedError.ResolutionMethod.SOLUTION_REVEALED,
		)
		DetectedError.objects.create(
			submission=self.other_submission,
			error_category=DetectedError.Category.PREPOSITION,
			severity=DetectedError.Severity.MEDIUM,
			start_offset=4,
			end_offset=9,
			original_text='gehe',
			hint_text='Check the preposition.',
			correct_solution='nach',
		)

		CorrectionAttempt.objects.create(
			error=self.article_error,
			student=self.student,
			attempt_number=1,
			attempted_text='Die',
			is_correct=True,
		)
		CorrectionAttempt.objects.create(
			error=self.preposition_error,
			student=self.student,
			attempt_number=1,
			attempted_text='in',
			is_correct=False,
			hint_shown=True,
		)
		CorrectionAttempt.objects.create(
			error=self.classmate_error,
			student=self.classmate,
			attempt_number=1,
			attempted_text='park',
			is_correct=False,
			hint_shown=True,
		)
		CorrectionAttempt.objects.create(
			error=self.classmate_error,
			student=self.classmate,
			attempt_number=2,
			attempted_text='park',
			is_correct=False,
			solution_shown=True,
		)

		LearnerErrorSummary.objects.create(
			student=self.student,
			submission=self.submission,
			error_category=DetectedError.Category.ARTICLE,
			total_errors=3,
			first_attempt_successes=1,
			avg_hints_used=0.5,
		)
		LearnerErrorSummary.objects.create(
			student=self.student,
			submission=self.second_submission,
			error_category=DetectedError.Category.PREPOSITION,
			total_errors=2,
			first_attempt_successes=0,
			avg_hints_used=1.0,
		)
		LearnerErrorSummary.objects.create(
			student=self.classmate,
			submission=self.classmate_submission,
			error_category=DetectedError.Category.SPELLING,
			total_errors=1,
			first_attempt_successes=0,
			avg_hints_used=1.0,
		)

	def test_student_progress_returns_dashboard_payload(self):
		self.client.force_authenticate(user=self.student)
		url = reverse('student-progress', kwargs={'student_id': self.student.id})

		response = self.client.get(url)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['student']['id'], self.student.id)
		self.assertEqual(response.data['overview']['submission_count'], 2)
		self.assertEqual(response.data['overview']['total_errors'], 2)
		self.assertEqual(response.data['overview']['manual_reveal_count'], 1)
		self.assertEqual(len(response.data['submissions']), 2)
		self.assertEqual(response.data['submissions'][0]['submission_id'], self.submission.id)
		self.assertEqual(response.data['submissions'][1]['submission_id'], self.second_submission.id)
		self.assertEqual(response.data['submissions'][0]['categories'][0]['error_category'], 'article')
		self.assertEqual(response.data['category_breakdown'][0]['error_category'], 'article')
		self.assertEqual(response.data['category_breakdown'][0]['timeline'][0]['submission_id'], self.submission.id)

	def test_teacher_can_view_student_progress_for_own_classroom(self):
		self.client.force_authenticate(user=self.teacher)
		url = reverse('student-progress', kwargs={'student_id': self.student.id})

		response = self.client.get(url)

		self.assertEqual(response.status_code, 200)

	def test_teacher_cannot_view_student_progress_outside_owned_classroom(self):
		self.client.force_authenticate(user=self.teacher)
		url = reverse('student-progress', kwargs={'student_id': self.other_student.id})

		response = self.client.get(url)

		self.assertEqual(response.status_code, 403)
		self.assertEqual(response.data['detail'], 'You do not have access to this student.')

	def test_teacher_cannot_view_patterns_for_other_teachers_classroom(self):
		self.client.force_authenticate(user=self.teacher)
		url = reverse('classroom-patterns', kwargs={'classroom_id': self.other_classroom.id})

		response = self.client.get(url)

		self.assertEqual(response.status_code, 403)
		self.assertEqual(response.data['detail'], 'You are not a teacher in this classroom.')

	def test_teacher_classroom_patterns_returns_dashboard_payload(self):
		self.client.force_authenticate(user=self.teacher)
		url = reverse('classroom-patterns', kwargs={'classroom_id': self.classroom.id})

		response = self.client.get(url)

		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['classroom']['id'], self.classroom.id)
		self.assertEqual(response.data['overview']['student_count'], 2)
		self.assertEqual(response.data['overview']['submission_count'], 3)
		self.assertEqual(response.data['overview']['total_errors'], 3)
		self.assertEqual(response.data['overview']['manual_reveal_count'], 1)
		self.assertEqual(len(response.data['timeline']), 3)
		self.assertEqual(response.data['category_breakdown'][0]['error_category'], 'article')
		self.assertEqual(response.data['students'][0]['student_id'], self.student.id)
		self.assertEqual(response.data['students'][0]['top_error_category'], 'article')
		self.assertEqual(response.data['students'][1]['student_id'], self.classmate.id)
