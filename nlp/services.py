import logging
from typing import Protocol

import requests
from django.conf import settings

from feedback.models import DetectedError
from submissions.models import TextSubmission
from .spacy_processor import SpacyTextProcessor, SentenceSpan

logger = logging.getLogger(__name__)


# ── Strategy Pattern: pluggable error detection backends ──

class ErrorDetector(Protocol):
    def detect(self, text: str, language: str) -> list[dict]:
        ...


class LanguageToolClient:
    """Calls the self-hosted LanguageTool REST API (/v2/check)."""

    CATEGORY_MAP = {
        'GRAMMAR': DetectedError.Category.GRAMMAR,
        'TYPOS': DetectedError.Category.SPELLING,
        'SPELLING': DetectedError.Category.SPELLING,
        'PUNCTUATION': DetectedError.Category.PUNCTUATION,
        'TYPOGRAPHY': DetectedError.Category.PUNCTUATION,
        'CASING': DetectedError.Category.SPELLING,
    }

    def __init__(self):
        self.base_url = settings.MRGRAMMAR['LANGUAGETOOL_URL']

    def detect(self, text: str, language: str) -> list[dict]:
        try:
            response = requests.post(
                f'{self.base_url}/check',
                data={'text': text, 'language': language},
                timeout=30,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error('LanguageTool request failed: %s', e)
            return []

        matches = self._extract_matches(response)
        return self._parse_matches(matches, text, base_offset=0)

    def detect_by_sentences(
        self,
        sentences: list[SentenceSpan],
        language: str,
    ) -> list[dict]:
        """Send each sentence individually and remap offsets to original text."""
        all_errors = []
        for sentence in sentences:
            try:
                response = requests.post(
                    f'{self.base_url}/check',
                    data={'text': sentence.text, 'language': language},
                    timeout=30,
                )
                response.raise_for_status()
            except requests.RequestException as e:
                logger.error(
                    'LanguageTool request failed for sentence at offset %d: %s',
                    sentence.start_offset, e,
                )
                continue

            matches = self._extract_matches(
                response,
                context=f' for sentence at offset {sentence.start_offset}',
            )
            errors = self._parse_matches(
                matches, sentence.text, base_offset=sentence.start_offset,
            )
            all_errors.extend(errors)
        return all_errors

    def _extract_matches(self, response, context: str = '') -> list[dict]:
        try:
            payload = response.json()
        except ValueError as e:
            logger.error('LanguageTool returned invalid JSON%s: %s', context, e)
            return []

        matches = payload.get('matches', [])
        if not isinstance(matches, list):
            logger.warning('LanguageTool returned malformed matches payload%s: %s', context, payload)
            return []
        return matches

    def _parse_matches(
        self,
        matches: list[dict],
        text: str,
        base_offset: int = 0,
    ) -> list[dict]:
        errors = []
        for match in matches:
            try:
                start_offset = int(match.get('offset', 0))
                length = int(match.get('length', 0))
            except (TypeError, ValueError):
                logger.warning('Skipping malformed LanguageTool match offsets: %s', match)
                continue

            end_offset = start_offset + length
            if start_offset < 0 or length <= 0 or end_offset > len(text):
                logger.warning(
                    'Skipping out-of-range LanguageTool match: start=%s length=%s text_len=%s',
                    start_offset,
                    length,
                    len(text),
                )
                continue

            replacements = match.get('replacements', [])
            best_replacement = ''
            if replacements and isinstance(replacements[0], dict):
                best_replacement = str(replacements[0].get('value', ''))

            lt_category = str(match.get('rule', {}).get('category', {}).get('id', ''))

            local_start = start_offset
            local_end = end_offset

            errors.append({
                'start_offset': base_offset + local_start,
                'end_offset': base_offset + local_end,
                'original_text': text[local_start:local_end],
                'correct_solution': best_replacement,
                'hint_text': str(match.get('message', '')),
                'error_category': self._map_category(lt_category, match),
                'languagetool_rule_id': str(match.get('rule', {}).get('id', '')),
            })
        return errors

    def _map_category(self, lt_category: str, match: dict) -> str:
        rule_id = match.get('rule', {}).get('id', '').upper()

        if 'ARTICLE' in rule_id or 'DER_DIE_DAS' in rule_id:
            return DetectedError.Category.ARTICLE
        if 'PREPOSITION' in rule_id or 'PRAEP' in rule_id:
            return DetectedError.Category.PREPOSITION
        if 'TENSE' in rule_id or 'VERB' in rule_id:
            return DetectedError.Category.VERB_TENSE

        return self.CATEGORY_MAP.get(lt_category, DetectedError.Category.OTHER)


class SpacyGrammarDetector: 
    #own commentim not sure if this is really necessary, if I will use an LLM for the things that languagetool misses, or idk...
    """
    Uses spaCy's German model to catch errors that LanguageTool misses:
    - Out-of-vocabulary words (misspellings like 'hauptjobb', 'bestehd')
    - Capitalization of nouns (German nouns must be capitalized)
    - Basic case/gender agreement on articles + nouns
    """

    # Words that are commonly lowercase even though they could look like nouns
    LOWERCASE_OK = frozenset({
        'ich', 'du', 'er', 'sie', 'es', 'wir', 'ihr', 'und', 'oder', 'aber',
        'denn', 'weil', 'dass', 'wenn', 'als', 'ob', 'nicht', 'auch', 'noch',
        'schon', 'sehr', 'ganz', 'hier', 'dort', 'jetzt', 'dann', 'nur',
        'gerade', 'immer', 'nie', 'oft', 'viel', 'wenig', 'mehr', 'so',
        'ja', 'nein', 'kein', 'keine', 'keinen', 'keine', 'keinem', 'keiner',
    })

    def __init__(self):
        self.processor = SpacyTextProcessor()

    def detect(self, text: str, language: str) -> list[dict]:
        if language not in ('de', 'de-DE', 'de-AT', 'de-CH'):
            return []

        doc = self.processor.make_doc(text)
        errors = []

        for token in doc:
            # Skip punctuation, spaces, numbers
            if token.is_punct or token.is_space or token.like_num:
                continue
            # Skip very short tokens
            if len(token.text) < 2:
                continue

            # ── Check 1: Out-of-vocabulary (likely misspelling) ──
            if not token.is_oov:
                # Token is in vocabulary — check capitalization for nouns
                self._check_noun_capitalization(token, doc, errors, text)
            else:
                # Token is OOV — likely a spelling error
                self._check_oov_token(token, doc, errors, text)

        return errors

    def _check_oov_token(self, token, doc, errors: list, text: str):
        """Flag out-of-vocabulary tokens as potential spelling errors."""
        # Skip if it's a recognized named entity (person, location, org)
        if token.ent_type_ in ('PER', 'LOC', 'ORG'):
            return

        # Try to find the closest in-vocabulary word
        suggestion = self._find_similar_word(token)
        hint = f'"{token.text}" wurde nicht im Wörterbuch gefunden.'
        if suggestion:
            hint = f'Meinten Sie "{suggestion}"?'

        errors.append({
            'start_offset': token.idx,
            'end_offset': token.idx + len(token.text),
            'original_text': token.text,
            'correct_solution': suggestion or token.text,
            'hint_text': hint,
            'error_category': DetectedError.Category.SPELLING,
            'languagetool_rule_id': 'SPACY_OOV',
        })

    def _check_noun_capitalization(self, token, doc, errors: list, text: str):
        """In German, nouns must be capitalized."""
        if token.pos_ != 'NOUN':
            return
        if token.text[0].isupper():
            return
        if token.text.lower() in self.LOWERCASE_OK:
            return
        # Skip tokens that are part of named entities
        if token.ent_type_:
            return

        capitalized = token.text[0].upper() + token.text[1:]
        errors.append({
            'start_offset': token.idx,
            'end_offset': token.idx + len(token.text),
            'original_text': token.text,
            'correct_solution': capitalized,
            'hint_text': f'Deutsche Substantive werden großgeschrieben: "{capitalized}".',
            'error_category': DetectedError.Category.SPELLING,
            'languagetool_rule_id': 'SPACY_NOUN_CAPITALIZATION',
        })

    def _find_similar_word(self, token) -> str:
        """Use Levenshtein distance over the model's vector keys to suggest corrections."""
        from Levenshtein import distance as lev_distance

        nlp = self.processor.nlp
        token_text = token.text.lower()
        target_len = len(token_text)

        best_word = ''
        best_dist = float('inf')

        # The vectors table contains the actual word list (~20k words)
        for key in nlp.vocab.vectors.keys():
            word = nlp.vocab.strings[key]
            if not word.isalpha():
                continue
            if abs(len(word) - target_len) > 2:
                continue

            dist = lev_distance(token_text, word.lower())
            if dist < best_dist:
                best_dist = dist
                best_word = word

        # Only suggest if edit distance is small (1-2 edits)
        if best_dist <= 2 and best_word:
            # Preserve original capitalization intent
            if token.text[0].isupper():
                best_word = best_word[0].upper() + best_word[1:]
            return best_word
        return ''


class ErrorDetectionService:
    """Orchestrates error detection using one or more backends (Strategy pattern)."""

    def __init__(self, detectors: list[ErrorDetector] | None = None):
        if detectors is None:
            self.detectors = [LanguageToolClient(), SpacyGrammarDetector()]
        else:
            self.detectors = detectors
        self.spacy_processor = SpacyTextProcessor()
        self.use_sentence_split = settings.MRGRAMMAR.get('SPACY_SENTENCE_SPLIT', True)

    def analyze(self, submission: TextSubmission) -> list[DetectedError]:
        text = submission.content
        submission_id = getattr(submission, 'id', None)

        # ── Create spaCy doc for POS/NER analysis ──
        doc = self.spacy_processor.make_doc(text)
        sentences = self.spacy_processor.split_sentences(text) if self.use_sentence_split else []

        # ── Detection ──
        all_raw_errors = []
        for detector in self.detectors:
            try:
                if self.use_sentence_split and hasattr(detector, 'detect_by_sentences'):
                    raw_errors = detector.detect_by_sentences(sentences, submission.language)
                else:
                    raw_errors = detector.detect(text, submission.language)
            except Exception:
                logger.exception('Detector failed for submission_id=%s', submission_id)
                continue
            all_raw_errors.extend(raw_errors)

        # Deduplicate by offset range
        seen_ranges = set()
        unique_errors = []
        for err in all_raw_errors:
            try:
                start_offset = int(err.get('start_offset', 0))
                end_offset = int(err.get('end_offset', 0))
            except (AttributeError, TypeError, ValueError):
                logger.warning('Skipping malformed raw error payload: %s', err)
                continue

            if start_offset < 0 or end_offset <= start_offset or end_offset > len(submission.content):
                logger.warning(
                    'Skipping invalid raw error range: start=%s end=%s content_len=%s',
                    start_offset,
                    end_offset,
                    len(submission.content),
                )
                continue

            key = (start_offset, end_offset)
            if key not in seen_ranges:
                seen_ranges.add(key)
                unique_errors.append({
                    'start_offset': start_offset,
                    'end_offset': end_offset,
                    'original_text': str(err.get('original_text', submission.content[start_offset:end_offset])),
                    'hint_text': str(err.get('hint_text', '')),
                    'correct_solution': str(err.get('correct_solution', '')),
                    'error_category': str(err.get('error_category', DetectedError.Category.OTHER)),
                    'languagetool_rule_id': str(err.get('languagetool_rule_id', '')),
                })

        # ── Post-processing: enrich with spaCy ──
        detected = []
        valid_categories = {choice for choice, _label in DetectedError.Category.choices}
        for err in unique_errors:
            try:
                enhanced_category = self.spacy_processor.categorize_error(
                    original_text=err['original_text'],
                    lt_category=err['error_category'],
                    lt_rule_id=err.get('languagetool_rule_id', ''),
                    doc=doc,
                    start_offset=err['start_offset'],
                )
                if enhanced_category not in valid_categories:
                    enhanced_category = DetectedError.Category.OTHER

                error_context = self.spacy_processor.extract_error_context(
                    doc, err['start_offset'], err['end_offset'],
                )
                spacy_pos = self.spacy_processor.get_pos_tag(doc, err['start_offset'])

                detected.append(
                    DetectedError.objects.create(
                        submission=submission,
                        error_category=enhanced_category,
                        start_offset=err['start_offset'],
                        end_offset=err['end_offset'],
                        original_text=err['original_text'],
                        hint_text=err['hint_text'],
                        correct_solution=err['correct_solution'],
                        languagetool_rule_id=err.get('languagetool_rule_id', ''),
                        spacy_pos_tag=spacy_pos,
                        error_context=error_context,
                    )
                )
            except Exception:
                logger.exception('Failed creating DetectedError for submission_id=%s payload=%s', submission_id, err)

        return detected
