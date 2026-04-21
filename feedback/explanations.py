from __future__ import annotations

import logging

import requests
from django.conf import settings

from .models import DetectedError
from .presentation import derive_display_group, get_display_label


logger = logging.getLogger(__name__)


class ExplanationGenerationService:
    def __init__(self):
        config = settings.MRGRAMMAR
        self.enabled = config.get('ENABLE_LLM_EXPLANATIONS', True)
        self.base_url = config.get('OLLAMA_BASE_URL', 'http://10.0.0.4:11434').rstrip('/')
        self.model = config.get('OLLAMA_MODEL', 'gemma4:26b')
        self.timeout = config.get('OLLAMA_TIMEOUT_SECONDS', 15)
        self.temperature = config.get('OLLAMA_EXPLANATION_TEMPERATURE', 0.2)

    def generate(self, error: DetectedError, attempted_text: str = '') -> str:
        if not self.enabled:
            return self._fallback(error, attempted_text)

        prompt = self._build_prompt(error, attempted_text)
        try:
            response = requests.post(
                f'{self.base_url}/api/generate',
                json={
                    'model': self.model,
                    'prompt': prompt,
                    'stream': False,
                    'options': {
                        'temperature': self.temperature,
                    },
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning('Explanation generation failed for error_id=%s: %s', error.id, exc)
            return self._fallback(error, attempted_text)

        explanation = str(payload.get('response', '')).strip()
        if not explanation:
            return self._fallback(error, attempted_text)
        return explanation

    def _build_prompt(self, error: DetectedError, attempted_text: str) -> str:
        display_group = get_display_label(derive_display_group(error))
        context = error.error_context or {}
        return (
            'You are helping a German learner understand one correction. '
            'Write 2 short sentences in simple English. Do not greet the user. '
            'Do not mention internal tooling. Focus on why the learner answer is wrong and why the correct answer fits better.\n\n'
            f'Error group: {display_group}\n'
            f'Original text: {error.original_text}\n'
            f'Student answer: {attempted_text or "(not provided)"}\n'
            f'Correct answer: {error.correct_solution}\n'
            f'Hint: {error.hint_text or "(none)"}\n'
            f'POS tag: {error.spacy_pos_tag or "(unknown)"}\n'
            f'Context: {context}'
        )

    def _fallback(self, error: DetectedError, attempted_text: str) -> str:
        if error.hint_text:
            return (
                f'Your answer "{attempted_text}" does not match the expected correction "{error.correct_solution}". '
                f'{error.hint_text}'
            ).strip()

        return (
            f'Your answer "{attempted_text}" does not match the expected correction '
            f'"{error.correct_solution}" for this error.'
        )