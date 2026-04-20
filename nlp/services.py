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

        matches = response.json().get('matches', [])
        errors = []

        for match in matches:
            replacements = match.get('replacements', [])
            best_replacement = replacements[0]['value'] if replacements else ''
            lt_category = match.get('rule', {}).get('category', {}).get('id', '')

            errors.append({
                'start_offset': match['offset'],
                'end_offset': match['offset'] + match['length'],
                'original_text': text[match['offset']:match['offset'] + match['length']],
                'correct_solution': best_replacement,
                'hint_text': match.get('message', ''),
                'error_category': self._map_category(lt_category, match),
                'languagetool_rule_id': match.get('rule', {}).get('id', ''),
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
            raw_errors = detector.detect(submission.content, submission.language)
            all_raw_errors.extend(raw_errors)

        # Deduplicate by offset range
        seen_ranges = set()
        unique_errors = []
        for err in all_raw_errors:
            key = (err['start_offset'], err['end_offset'])
            if key not in seen_ranges:
                seen_ranges.add(key)
                unique_errors.append(err)

        detected = []
        for err in unique_errors:
            detected.append(
                DetectedError.objects.create(
                    submission=submission,
                    error_category=err['error_category'],
                    start_offset=err['start_offset'],
                    end_offset=err['end_offset'],
                    original_text=err['original_text'],
                    hint_text=err['hint_text'],
                    correct_solution=err['correct_solution'],
                    languagetool_rule_id=err.get('languagetool_rule_id', ''),
                )
            )

        return detected
