import logging
from typing import Protocol

import requests
from django.conf import settings

from feedback.models import DetectedError
from submissions.models import TextSubmission

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

        try:
            payload = response.json()
        except ValueError as e:
            logger.error('LanguageTool returned invalid JSON: %s', e)
            return []

        matches = payload.get('matches', [])
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

            errors.append({
                'start_offset': start_offset,
                'end_offset': end_offset,
                'original_text': text[start_offset:end_offset],
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


class ErrorDetectionService:
    """Orchestrates error detection using one or more backends (Strategy pattern)."""

    def __init__(self, detectors: list[ErrorDetector] | None = None):
        if detectors is None:
            self.detectors = [LanguageToolClient()]
        else:
            self.detectors = detectors

    def analyze(self, submission: TextSubmission) -> list[DetectedError]:
        all_raw_errors = []
        for detector in self.detectors:
            try:
                raw_errors = detector.detect(submission.content, submission.language)
            except Exception:
                logger.exception('Detector failed for submission_id=%s', submission.id)
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

        detected = []
        for err in unique_errors:
            category = err.get('error_category', DetectedError.Category.OTHER)
            valid_categories = {choice for choice, _label in DetectedError.Category.choices}
            if category not in valid_categories:
                category = DetectedError.Category.OTHER

            try:
                detected.append(
                    DetectedError.objects.create(
                        submission=submission,
                        error_category=category,
                        start_offset=err['start_offset'],
                        end_offset=err['end_offset'],
                        original_text=err['original_text'],
                        hint_text=err['hint_text'],
                        correct_solution=err['correct_solution'],
                        languagetool_rule_id=err.get('languagetool_rule_id', ''),
                    )
                )
            except Exception:
                logger.exception('Failed creating DetectedError for submission_id=%s payload=%s', submission.id, err)

        return detected
