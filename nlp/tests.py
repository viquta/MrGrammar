from unittest.mock import MagicMock, patch

import requests
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
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
        'nlp.services.LanguageToolClient.detect_by_sentences',
        return_value=[
            {
                'start_offset': 0,
                'end_offset': 2,
                'error_category': 'grammar',
                'original_text': 'Ic',
                'hint_text': 'h',
                'correct_solution': 'Ich',
            },
            {'start_offset': 'bad', 'end_offset': 4, 'error_category': 'grammar'},
            {'start_offset': 3, 'end_offset': 2, 'error_category': 'grammar'},
        ],
    )
    @patch('nlp.services.SpacyGrammarDetector.detect', return_value=[])
    @patch('nlp.services.SpacyTextProcessor')
    def test_analyze_ignores_malformed_errors_and_completes(
        self,
        MockProcessor,
        _mock_spacy_detect,
        _mock_detect_by_sentences,
    ):
        processor_instance = MockProcessor.return_value
        processor_instance.make_doc.return_value = MagicMock()
        processor_instance.split_sentences.return_value = []
        processor_instance.categorize_error.return_value = DetectedError.Category.GRAMMAR
        processor_instance.extract_error_context.return_value = {}
        processor_instance.get_pos_tag.return_value = 'NOUN'

        url = reverse('analyze-submission', kwargs={'submission_id': self.submission.id})
        response = self.client.post(url, data={}, format='json')

        self.submission.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.submission.status, TextSubmission.Status.IN_REVIEW)
        self.assertEqual(DetectedError.objects.filter(submission=self.submission).count(), 1)


# ── SpacyTextProcessor tests ──

class SpacyTextProcessorCleanTextTest(TestCase):
    def setUp(self):
        with patch('nlp.spacy_processor.spacy.load'):
            from nlp.spacy_processor import SpacyTextProcessor
            self.processor = SpacyTextProcessor()

    def test_collapse_whitespace(self):
        self.assertEqual(
            self.processor.clean_text('Hallo   Welt'),
            'Hallo Welt',
        )

    def test_strip_non_breaking_spaces(self):
        self.assertEqual(
            self.processor.clean_text('Hallo\u00a0Welt'),
            'Hallo Welt',
        )

    def test_preserve_newlines(self):
        result = self.processor.clean_text('Zeile eins.\nZeile zwei.')
        self.assertIn('\n', result)

    def test_unicode_normalization(self):
        # ä as combining sequence → composed NFC
        decomposed = 'a\u0308'  # ä decomposed
        result = self.processor.clean_text(decomposed)
        self.assertEqual(result, 'ä')


class SpacyTextProcessorSentenceSplitTest(TestCase):
    """Test sentence splitting with offset mapping using a real spaCy model."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            import spacy
            cls.nlp = spacy.load('de_core_news_md')
        except OSError:
            cls.nlp = None

    def setUp(self):
        if self.nlp is None:
            self.skipTest('spaCy model de_core_news_md not installed')
        from nlp.spacy_processor import SpacyTextProcessor, _SpacyModelHolder
        # Inject the pre-loaded model
        holder = _SpacyModelHolder.get()
        holder._nlp = self.nlp
        self.processor = SpacyTextProcessor()

    def test_offsets_map_back_to_original(self):
        text = 'Ich gehe nach Hause. Er bleibt hier.'
        sentences = self.processor.split_sentences(text)
        self.assertGreaterEqual(len(sentences), 2)
        for sent in sentences:
            self.assertEqual(
                text[sent.start_offset:sent.end_offset].strip(),
                sent.text.strip(),
                f'Offset mismatch for sentence: {sent.text!r}',
            )

    def test_umlauts_and_eszett(self):
        text = 'Die Stra\u00dfe ist gro\u00df. \u00dcber den Fl\u00fcssen liegt Nebel.'
        sentences = self.processor.split_sentences(text)
        for sent in sentences:
            self.assertEqual(
                text[sent.start_offset:sent.end_offset].strip(),
                sent.text.strip(),
            )


class SpacyTextProcessorCategorizeTest(TestCase):
    """Test POS-based category overrides."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            import spacy
            cls.nlp = spacy.load('de_core_news_md')
        except OSError:
            cls.nlp = None

    def setUp(self):
        if self.nlp is None:
            self.skipTest('spaCy model de_core_news_md not installed')
        from nlp.spacy_processor import SpacyTextProcessor, _SpacyModelHolder
        holder = _SpacyModelHolder.get()
        holder._nlp = self.nlp
        self.processor = SpacyTextProcessor()

    def test_determiner_becomes_article(self):
        doc = self.nlp('Der Hund ist gro\u00df.')
        # "Der" is at offset 0, POS=DET
        result = self.processor.categorize_error(
            'Der', DetectedError.Category.GRAMMAR, '', doc, 0,
        )
        self.assertEqual(result, DetectedError.Category.ARTICLE)

    def test_preposition_becomes_preposition(self):
        doc = self.nlp('Ich gehe nach Hause.')
        # "nach" starts at offset 9
        result = self.processor.categorize_error(
            'nach', DetectedError.Category.GRAMMAR, '', doc, 9,
        )
        self.assertEqual(result, DetectedError.Category.PREPOSITION)

    def test_verb_becomes_verb_tense(self):
        doc = self.nlp('Ich gehe nach Hause.')
        # "gehe" starts at offset 4
        result = self.processor.categorize_error(
            'gehe', DetectedError.Category.OTHER, '', doc, 4,
        )
        self.assertEqual(result, DetectedError.Category.VERB_TENSE)

    def test_noun_keeps_original_category(self):
        doc = self.nlp('Der Hund ist gro\u00df.')
        # "Hund" at offset 4, POS=NOUN — no override expected
        result = self.processor.categorize_error(
            'Hund', DetectedError.Category.SPELLING, '', doc, 4,
        )
        self.assertEqual(result, DetectedError.Category.SPELLING)


# ── LanguageToolClient offset remapping test ──

class LanguageToolClientSentenceDetectTest(TestCase):
    """Test that detect_by_sentences remaps offsets correctly."""

    @override_settings(MRGRAMMAR={
        'LANGUAGETOOL_URL': 'http://localhost:8010/v2',
        'SPACY_MODEL': 'de_core_news_md',
        'SPACY_SENTENCE_SPLIT': True,
        'MAX_CORRECTION_ATTEMPTS': 3,
        'HINT_THRESHOLD': 1,
        'SUPPORTED_LANGUAGES': ['de'],
    })
    def test_offset_remapping(self):
        from nlp.services import LanguageToolClient
        from nlp.spacy_processor import SentenceSpan

        client = LanguageToolClient()

        sentences = [
            SentenceSpan(text='Ich gehe.', start_offset=0, end_offset=9),
            SentenceSpan(text='Er bleiben hier.', start_offset=10, end_offset=26),
        ]

        # Mock a LanguageTool response for the second sentence only
        mock_lt_response = {
            'matches': [{
                'offset': 3,   # "bleiben" starts at offset 3 within "Er bleiben hier."
                'length': 7,
                'replacements': [{'value': 'bleibt'}],
                'message': 'Verb conjugation error',
                'rule': {'id': 'VERB_CONJ', 'category': {'id': 'GRAMMAR'}},
            }],
        }

        def mock_post(url, data, timeout):
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            if 'bleiben' in data.get('text', ''):
                resp.json.return_value = mock_lt_response
            else:
                resp.json.return_value = {'matches': []}
            return resp

        with patch('nlp.services.requests.post', side_effect=mock_post):
            errors = client.detect_by_sentences(sentences, 'de')

        self.assertEqual(len(errors), 1)
        # Offset should be remapped: sentence start (10) + local offset (3)
        self.assertEqual(errors[0]['start_offset'], 13)
        self.assertEqual(errors[0]['end_offset'], 20)


MRGRAMMAR_SETTINGS = {
    'LANGUAGETOOL_URL': 'http://localhost:8010/v2',
    'SPACY_MODEL': 'de_core_news_md',
    'SPACY_SENTENCE_SPLIT': True,
    'MAX_CORRECTION_ATTEMPTS': 3,
    'HINT_THRESHOLD': 1,
    'SUPPORTED_LANGUAGES': ['de'],
}


# ── LanguageToolClient.detect() tests ──

@override_settings(MRGRAMMAR=MRGRAMMAR_SETTINGS)
class LanguageToolClientDetectTest(TestCase):
    """Test the detect() method of LanguageToolClient."""

    def setUp(self):
        from nlp.services import LanguageToolClient
        self.client = LanguageToolClient()

    def _make_lt_response(self, matches):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {'matches': matches}
        return resp

    @patch('nlp.services.requests.post')
    def test_successful_detection(self, mock_post):
        mock_post.return_value = self._make_lt_response([{
            'offset': 4,
            'length': 4,
            'replacements': [{'value': 'geht'}],
            'message': 'Verb should be singular.',
            'rule': {'id': 'VERB_FORM', 'category': {'id': 'GRAMMAR'}},
        }])

        errors = self.client.detect('Ich gehe nach Hause.', 'de')

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['start_offset'], 4)
        self.assertEqual(errors[0]['end_offset'], 8)
        self.assertEqual(errors[0]['original_text'], 'gehe')
        self.assertEqual(errors[0]['correct_solution'], 'geht')
        self.assertEqual(errors[0]['hint_text'], 'Verb should be singular.')
        self.assertEqual(errors[0]['languagetool_rule_id'], 'VERB_FORM')

    @patch('nlp.services.requests.post')
    def test_empty_matches(self, mock_post):
        mock_post.return_value = self._make_lt_response([])
        errors = self.client.detect('Alles korrekt.', 'de')
        self.assertEqual(errors, [])

    @patch('nlp.services.requests.post')
    def test_request_exception_returns_empty(self, mock_post):
        mock_post.side_effect = requests.RequestException('Connection refused')
        errors = self.client.detect('Ich gehe.', 'de')
        self.assertEqual(errors, [])

    @patch('nlp.services.requests.post')
    def test_no_replacements_gives_empty_solution(self, mock_post):
        mock_post.return_value = self._make_lt_response([{
            'offset': 0,
            'length': 3,
            'replacements': [],
            'message': 'Possible error.',
            'rule': {'id': 'MISC', 'category': {'id': 'GRAMMAR'}},
        }])

        errors = self.client.detect('Ich gehe.', 'de')
        self.assertEqual(errors[0]['correct_solution'], '')

    @patch('nlp.services.requests.post')
    def test_multiple_matches(self, mock_post):
        mock_post.return_value = self._make_lt_response([
            {
                'offset': 0, 'length': 3,
                'replacements': [{'value': 'Der'}],
                'message': 'Wrong article.',
                'rule': {'id': 'DER_DIE_DAS', 'category': {'id': 'GRAMMAR'}},
            },
            {
                'offset': 10, 'length': 5,
                'replacements': [{'value': 'geht'}],
                'message': 'Verb form.',
                'rule': {'id': 'VERB_FORM', 'category': {'id': 'GRAMMAR'}},
            },
        ])

        errors = self.client.detect('Die Hund  gehts nach Hause.', 'de')
        self.assertEqual(len(errors), 2)
        self.assertEqual(errors[0]['start_offset'], 0)
        self.assertEqual(errors[1]['start_offset'], 10)


# ── LanguageToolClient._map_category() tests ──

@override_settings(MRGRAMMAR=MRGRAMMAR_SETTINGS)
class LanguageToolClientCategoryMapTest(TestCase):
    """Test category mapping from LanguageTool categories to DetectedError categories."""

    def setUp(self):
        from nlp.services import LanguageToolClient
        self.client = LanguageToolClient()

    def _match(self, rule_id='', lt_category=''):
        return {'rule': {'id': rule_id, 'category': {'id': lt_category}}}

    def test_grammar_maps_to_grammar(self):
        result = self.client._map_category('GRAMMAR', self._match())
        self.assertEqual(result, DetectedError.Category.GRAMMAR)

    def test_typos_maps_to_spelling(self):
        result = self.client._map_category('TYPOS', self._match())
        self.assertEqual(result, DetectedError.Category.SPELLING)

    def test_spelling_maps_to_spelling(self):
        result = self.client._map_category('SPELLING', self._match())
        self.assertEqual(result, DetectedError.Category.SPELLING)

    def test_punctuation_maps_to_punctuation(self):
        result = self.client._map_category('PUNCTUATION', self._match())
        self.assertEqual(result, DetectedError.Category.PUNCTUATION)

    def test_typography_maps_to_punctuation(self):
        result = self.client._map_category('TYPOGRAPHY', self._match())
        self.assertEqual(result, DetectedError.Category.PUNCTUATION)

    def test_casing_maps_to_spelling(self):
        result = self.client._map_category('CASING', self._match())
        self.assertEqual(result, DetectedError.Category.SPELLING)

    def test_unknown_category_maps_to_other(self):
        result = self.client._map_category('UNKNOWN_CAT', self._match())
        self.assertEqual(result, DetectedError.Category.OTHER)

    def test_article_rule_id_overrides(self):
        result = self.client._map_category('GRAMMAR', self._match(rule_id='DE_ARTICLE_MISSING'))
        self.assertEqual(result, DetectedError.Category.ARTICLE)

    def test_der_die_das_rule_id_overrides(self):
        result = self.client._map_category('GRAMMAR', self._match(rule_id='DER_DIE_DAS'))
        self.assertEqual(result, DetectedError.Category.ARTICLE)

    def test_preposition_rule_id_overrides(self):
        result = self.client._map_category('GRAMMAR', self._match(rule_id='PRAEP_AN'))
        self.assertEqual(result, DetectedError.Category.PREPOSITION)

    def test_verb_rule_id_overrides(self):
        result = self.client._map_category('GRAMMAR', self._match(rule_id='VERB_FORM'))
        self.assertEqual(result, DetectedError.Category.VERB_TENSE)

    def test_tense_rule_id_overrides(self):
        result = self.client._map_category('GRAMMAR', self._match(rule_id='PAST_TENSE'))
        self.assertEqual(result, DetectedError.Category.VERB_TENSE)


# ── LanguageToolClient.detect_by_sentences() error handling ──

@override_settings(MRGRAMMAR=MRGRAMMAR_SETTINGS)
class LanguageToolClientSentenceErrorHandlingTest(TestCase):
    """Test that HTTP failure on one sentence does not abort others."""

    @patch('nlp.services.requests.post')
    def test_failure_on_first_sentence_still_processes_second(self, mock_post):
        from nlp.services import LanguageToolClient
        from nlp.spacy_processor import SentenceSpan

        client = LanguageToolClient()

        sentences = [
            SentenceSpan(text='Erster Satz.', start_offset=0, end_offset=12),
            SentenceSpan(text='Zweiter Satz.', start_offset=13, end_offset=26),
        ]

        success_resp = MagicMock()
        success_resp.raise_for_status = MagicMock()
        success_resp.json.return_value = {'matches': [{
            'offset': 0, 'length': 7,
            'replacements': [{'value': 'Zweite'}],
            'message': 'Error found.',
            'rule': {'id': 'TEST', 'category': {'id': 'GRAMMAR'}},
        }]}

        # First call raises, second succeeds
        mock_post.side_effect = [
            requests.RequestException('timeout'),
            success_resp,
        ]

        errors = client.detect_by_sentences(sentences, 'de')
        self.assertEqual(len(errors), 1)
        # Offset remapped from sentence 2
        self.assertEqual(errors[0]['start_offset'], 13)


# ── SpacyGrammarDetector tests ──

@override_settings(MRGRAMMAR=MRGRAMMAR_SETTINGS)
class SpacyGrammarDetectorTest(TestCase):
    """Test SpacyGrammarDetector.detect() with mocked spaCy."""

    def _make_token(self, text, pos='NOUN', is_oov=False, is_punct=False,
                    is_space=False, like_num=False, ent_type_='', idx=0):
        token = MagicMock()
        token.text = text
        token.pos_ = pos
        token.is_oov = is_oov
        token.is_punct = is_punct
        token.is_space = is_space
        token.like_num = like_num
        token.ent_type_ = ent_type_
        token.idx = idx
        return token

    def _make_detector_with_doc(self, tokens):
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter(tokens))

        with patch('nlp.services.SpacyTextProcessor') as MockProcessor:
            processor_instance = MockProcessor.return_value
            processor_instance.make_doc.return_value = mock_doc
            from nlp.services import SpacyGrammarDetector
            detector = SpacyGrammarDetector()
        return detector

    def test_non_german_language_returns_empty(self):
        with patch('nlp.services.SpacyTextProcessor'):
            from nlp.services import SpacyGrammarDetector
            detector = SpacyGrammarDetector()
        self.assertEqual(detector.detect('Hello world', 'en'), [])

    def test_supported_german_variants(self):
        with patch('nlp.services.SpacyTextProcessor') as MockProcessor:
            processor_instance = MockProcessor.return_value
            mock_doc = MagicMock()
            mock_doc.__iter__ = MagicMock(return_value=iter([]))
            processor_instance.make_doc.return_value = mock_doc
            from nlp.services import SpacyGrammarDetector
            detector = SpacyGrammarDetector()

        for lang in ('de', 'de-DE', 'de-AT', 'de-CH'):
            result = detector.detect('Test', lang)
            self.assertEqual(result, [])

    def test_oov_token_produces_spelling_error(self):
        token = self._make_token('hauptjobb', is_oov=True, idx=0)
        detector = self._make_detector_with_doc([token])

        with patch.object(detector, '_find_similar_word', return_value='Hauptjob'):
            errors = detector.detect('hauptjobb', 'de')

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['error_category'], DetectedError.Category.SPELLING)
        self.assertEqual(errors[0]['languagetool_rule_id'], 'SPACY_OOV')
        self.assertEqual(errors[0]['correct_solution'], 'Hauptjob')

    def test_oov_token_without_suggestion(self):
        token = self._make_token('xyzqwk', is_oov=True, idx=0)
        detector = self._make_detector_with_doc([token])

        with patch.object(detector, '_find_similar_word', return_value=''):
            errors = detector.detect('xyzqwk', 'de')

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['correct_solution'], 'xyzqwk')
        self.assertIn('nicht im Wörterbuch', errors[0]['hint_text'])

    def test_oov_named_entity_not_flagged(self):
        token = self._make_token('München', is_oov=True, ent_type_='LOC', idx=0)
        detector = self._make_detector_with_doc([token])
        errors = detector.detect('München', 'de')
        self.assertEqual(errors, [])

    def test_lowercase_noun_produces_capitalization_error(self):
        token = self._make_token('hund', pos='NOUN', is_oov=False, idx=4)
        detector = self._make_detector_with_doc([token])
        errors = detector.detect('Der hund.', 'de')

        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['correct_solution'], 'Hund')
        self.assertEqual(errors[0]['languagetool_rule_id'], 'SPACY_NOUN_CAPITALIZATION')

    def test_capitalized_noun_not_flagged(self):
        token = self._make_token('Hund', pos='NOUN', is_oov=False, idx=4)
        detector = self._make_detector_with_doc([token])
        errors = detector.detect('Der Hund.', 'de')
        self.assertEqual(errors, [])

    def test_lowercase_ok_word_not_flagged(self):
        token = self._make_token('nicht', pos='NOUN', is_oov=False, idx=0)
        detector = self._make_detector_with_doc([token])
        errors = detector.detect('nicht', 'de')
        self.assertEqual(errors, [])

    def test_named_entity_noun_not_flagged_for_capitalization(self):
        token = self._make_token('test', pos='NOUN', is_oov=False, ent_type_='ORG', idx=0)
        detector = self._make_detector_with_doc([token])
        errors = detector.detect('test', 'de')
        self.assertEqual(errors, [])

    def test_punctuation_skipped(self):
        token = self._make_token('.', is_punct=True, pos='PUNCT', idx=0)
        detector = self._make_detector_with_doc([token])
        errors = detector.detect('.', 'de')
        self.assertEqual(errors, [])

    def test_space_skipped(self):
        token = self._make_token('  ', is_space=True, pos='SPACE', idx=0)
        detector = self._make_detector_with_doc([token])
        errors = detector.detect('  ', 'de')
        self.assertEqual(errors, [])

    def test_number_skipped(self):
        token = self._make_token('42', like_num=True, pos='NUM', idx=0)
        detector = self._make_detector_with_doc([token])
        errors = detector.detect('42', 'de')
        self.assertEqual(errors, [])

    def test_short_token_skipped(self):
        token = self._make_token('x', is_oov=True, idx=0)
        detector = self._make_detector_with_doc([token])
        errors = detector.detect('x', 'de')
        self.assertEqual(errors, [])


# ── SpacyGrammarDetector._find_similar_word() tests ──

@override_settings(MRGRAMMAR=MRGRAMMAR_SETTINGS)
class SpacyGrammarDetectorSimilarWordTest(TestCase):
    """Test _find_similar_word() with mocked vocab."""

    def _make_detector_with_vocab(self, vocab_words):
        """Create a detector whose processor.nlp.vocab has the given word list."""
        with patch('nlp.services.SpacyTextProcessor') as MockProcessor:
            processor_instance = MockProcessor.return_value
            mock_nlp = MagicMock()
            processor_instance.nlp = mock_nlp

            # Build mock vocab: keys → hash-like ints, strings → word lookup
            string_store = {}
            keys = []
            for i, word in enumerate(vocab_words):
                keys.append(i)
                string_store[i] = word

            mock_nlp.vocab.vectors.keys.return_value = keys
            mock_nlp.vocab.strings.__getitem__ = lambda self_inner, k: string_store[k]

            from nlp.services import SpacyGrammarDetector
            detector = SpacyGrammarDetector()
        return detector

    def test_close_match_returns_suggestion(self):
        detector = self._make_detector_with_vocab(['Hund', 'Katze', 'Haus'])
        token = MagicMock()
        token.text = 'Humd'  # edit distance 1 from 'Hund'

        result = detector._find_similar_word(token)
        self.assertEqual(result, 'Hund')

    def test_no_close_match_returns_empty(self):
        detector = self._make_detector_with_vocab(['Hund', 'Katze', 'Haus'])
        token = MagicMock()
        token.text = 'xyzabc'

        result = detector._find_similar_word(token)
        self.assertEqual(result, '')

    def test_preserves_uppercase_first_letter(self):
        detector = self._make_detector_with_vocab(['schule'])
        token = MagicMock()
        token.text = 'Schulo'  # close to 'schule', starts uppercase

        result = detector._find_similar_word(token)
        self.assertEqual(result, 'Schule')

    def test_exact_match_returns_word(self):
        detector = self._make_detector_with_vocab(['Haus'])
        token = MagicMock()
        token.text = 'haus'  # exact match (case-insensitive)

        result = detector._find_similar_word(token)
        self.assertEqual(result, 'Haus')


# ── ErrorDetectionService tests ──

@override_settings(MRGRAMMAR=MRGRAMMAR_SETTINGS)
class ErrorDetectionServiceAnalyzeTest(TestCase):
    """Test ErrorDetectionService.analyze() orchestration."""

    def _make_submission(self, content='Ich gehe nach Hause.', language='de'):
        submission = MagicMock()
        submission.content = content
        submission.language = language
        return submission

    @patch('nlp.services.DetectedError.objects.create')
    @patch('nlp.services.SpacyTextProcessor')
    def test_creates_detected_errors(self, MockProcessor, mock_create):
        from nlp.services import ErrorDetectionService

        mock_doc = MagicMock()
        processor_instance = MockProcessor.return_value
        processor_instance.make_doc.return_value = mock_doc
        processor_instance.split_sentences.return_value = []
        processor_instance.categorize_error.return_value = DetectedError.Category.GRAMMAR
        processor_instance.extract_error_context.return_value = {'tokens': []}
        processor_instance.get_pos_tag.return_value = 'NOUN'

        mock_detector = MagicMock()
        del mock_detector.detect_by_sentences
        mock_detector.detect.return_value = [{
            'start_offset': 0,
            'end_offset': 3,
            'original_text': 'Ich',
            'correct_solution': 'Mich',
            'hint_text': 'Wrong pronoun.',
            'error_category': DetectedError.Category.GRAMMAR,
            'languagetool_rule_id': 'PRONOUN',
        }]

        mock_create.return_value = MagicMock()

        service = ErrorDetectionService(detectors=[mock_detector])
        submission = self._make_submission()
        service.analyze(submission)

        mock_create.assert_called_once()
        kwargs = mock_create.call_args.kwargs
        self.assertEqual(kwargs['submission'], submission)
        self.assertEqual(kwargs['start_offset'], 0)
        self.assertEqual(kwargs['end_offset'], 3)
        self.assertEqual(kwargs['original_text'], 'Ich')
        self.assertEqual(kwargs['correct_solution'], 'Mich')
        self.assertEqual(kwargs['spacy_pos_tag'], 'NOUN')
        self.assertEqual(kwargs['error_context'], {'tokens': []})

    @patch('nlp.services.DetectedError.objects.create')
    @patch('nlp.services.SpacyTextProcessor')
    def test_sentence_split_calls_detect_by_sentences(self, MockProcessor, mock_create):
        from nlp.services import ErrorDetectionService
        from nlp.spacy_processor import SentenceSpan

        processor_instance = MockProcessor.return_value
        processor_instance.make_doc.return_value = MagicMock()
        processor_instance.split_sentences.return_value = [
            SentenceSpan('Satz eins.', 0, 10),
        ]
        processor_instance.categorize_error.return_value = DetectedError.Category.GRAMMAR
        processor_instance.extract_error_context.return_value = {}
        processor_instance.get_pos_tag.return_value = ''

        mock_detector = MagicMock()
        mock_detector.detect_by_sentences.return_value = [{
            'start_offset': 0, 'end_offset': 4,
            'original_text': 'Satz', 'correct_solution': 'Sätze',
            'hint_text': 'Plural.', 'error_category': 'grammar',
            'languagetool_rule_id': 'X',
        }]
        mock_create.return_value = MagicMock()

        service = ErrorDetectionService(detectors=[mock_detector])
        service.analyze(self._make_submission())

        mock_detector.detect_by_sentences.assert_called_once()
        mock_detector.detect.assert_not_called()

    @patch('nlp.services.DetectedError.objects.create')
    @patch('nlp.services.SpacyTextProcessor')
    def test_no_sentence_split_calls_detect(self, MockProcessor, mock_create):
        from nlp.services import ErrorDetectionService

        processor_instance = MockProcessor.return_value
        processor_instance.make_doc.return_value = MagicMock()
        processor_instance.categorize_error.return_value = DetectedError.Category.GRAMMAR
        processor_instance.extract_error_context.return_value = {}
        processor_instance.get_pos_tag.return_value = ''

        mock_detector = MagicMock()
        # Remove detect_by_sentences so hasattr returns False
        del mock_detector.detect_by_sentences
        mock_detector.detect.return_value = [{
            'start_offset': 0, 'end_offset': 3,
            'original_text': 'Ich', 'correct_solution': 'Mich',
            'hint_text': 'X.', 'error_category': 'grammar',
            'languagetool_rule_id': 'Y',
        }]
        mock_create.return_value = MagicMock()

        service = ErrorDetectionService(detectors=[mock_detector])
        service.analyze(self._make_submission())

        mock_detector.detect.assert_called_once()

    @patch('nlp.services.DetectedError.objects.create')
    @patch('nlp.services.SpacyTextProcessor')
    def test_deduplication_by_offset(self, MockProcessor, mock_create):
        from nlp.services import ErrorDetectionService

        processor_instance = MockProcessor.return_value
        processor_instance.make_doc.return_value = MagicMock()
        processor_instance.categorize_error.return_value = DetectedError.Category.SPELLING
        processor_instance.extract_error_context.return_value = {}
        processor_instance.get_pos_tag.return_value = ''

        error_a = {
            'start_offset': 0, 'end_offset': 5,
            'original_text': 'Hallo', 'correct_solution': 'Hello',
            'hint_text': 'X.', 'error_category': 'spelling',
            'languagetool_rule_id': 'A',
        }
        error_b = {
            'start_offset': 0, 'end_offset': 5,  # same range
            'original_text': 'Hallo', 'correct_solution': 'Hello',
            'hint_text': 'Y.', 'error_category': 'spelling',
            'languagetool_rule_id': 'B',
        }

        det1 = MagicMock()
        del det1.detect_by_sentences
        det1.detect.return_value = [error_a]

        det2 = MagicMock()
        del det2.detect_by_sentences
        det2.detect.return_value = [error_b]

        mock_create.return_value = MagicMock()

        service = ErrorDetectionService(detectors=[det1, det2])
        service.analyze(self._make_submission())

        # Only one DetectedError created despite two detectors returning same offset
        self.assertEqual(mock_create.call_count, 1)

    @patch('nlp.services.DetectedError.objects.create')
    @patch('nlp.services.SpacyTextProcessor')
    def test_spacy_post_processing_enriches_errors(self, MockProcessor, mock_create):
        from nlp.services import ErrorDetectionService

        mock_doc = MagicMock()
        processor_instance = MockProcessor.return_value
        processor_instance.make_doc.return_value = mock_doc
        processor_instance.categorize_error.return_value = DetectedError.Category.ARTICLE
        processor_instance.extract_error_context.return_value = {'tokens': [{'text': 'Der'}]}
        processor_instance.get_pos_tag.return_value = 'DET'

        mock_detector = MagicMock()
        del mock_detector.detect_by_sentences
        mock_detector.detect.return_value = [{
            'start_offset': 0, 'end_offset': 3,
            'original_text': 'Der', 'correct_solution': 'Die',
            'hint_text': 'Wrong article.',
            'error_category': DetectedError.Category.GRAMMAR,
            'languagetool_rule_id': 'ART',
        }]
        mock_create.return_value = MagicMock()

        service = ErrorDetectionService(detectors=[mock_detector])
        service.analyze(self._make_submission())

        kwargs = mock_create.call_args.kwargs
        # Category was overridden by spaCy categorize_error
        self.assertEqual(kwargs['error_category'], DetectedError.Category.ARTICLE)
        self.assertEqual(kwargs['spacy_pos_tag'], 'DET')
        self.assertEqual(kwargs['error_context'], {'tokens': [{'text': 'Der'}]})

        # Verify categorize_error was called with the right args
        processor_instance.categorize_error.assert_called_once_with(
            original_text='Der',
            lt_category=DetectedError.Category.GRAMMAR,
            lt_rule_id='ART',
            doc=mock_doc,
            start_offset=0,
        )


@override_settings(MRGRAMMAR=MRGRAMMAR_SETTINGS)
class ErrorDetectionServiceCustomDetectorsTest(TestCase):
    """Test that custom injected detectors are used exclusively."""

    @patch('nlp.services.DetectedError.objects.create')
    @patch('nlp.services.SpacyTextProcessor')
    def test_custom_detectors_only(self, MockProcessor, mock_create):
        from nlp.services import ErrorDetectionService

        processor_instance = MockProcessor.return_value
        processor_instance.make_doc.return_value = MagicMock()

        custom = MagicMock()
        del custom.detect_by_sentences
        custom.detect.return_value = []

        service = ErrorDetectionService(detectors=[custom])
        submission = MagicMock()
        submission.content = 'Test.'
        submission.language = 'de'
        service.analyze(submission)

        custom.detect.assert_called_once_with('Test.', 'de')
        self.assertEqual(len(service.detectors), 1)
