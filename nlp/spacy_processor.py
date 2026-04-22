import logging
import re
import unicodedata
from dataclasses import dataclass, field
from threading import Lock

import spacy
from django.conf import settings

from feedback.models import DetectedError

logger = logging.getLogger(__name__)


# ── Data classes ──

@dataclass
class SentenceSpan:
    text: str
    start_offset: int
    end_offset: int


@dataclass
class TokenInfo:
    text: str
    pos: str
    morph: dict = field(default_factory=dict)
    dep: str = ''
    is_entity: bool = False
    entity_label: str = ''


# ── Singleton model loader ──

class _SpacyModelHolder:
    """Thread-safe singleton to avoid reloading the ~40 MB model per request."""

    _instance = None
    _lock = Lock()

    def __init__(self):
        self._nlp = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @property
    def nlp(self):
        if self._nlp is None:
            model_name = settings.MRGRAMMAR.get('SPACY_MODEL', 'de_core_news_md')
            logger.info('Loading spaCy model: %s', model_name)
            self._nlp = spacy.load(model_name)
        return self._nlp


# ── Main processor ──

class SpacyTextProcessor:
    """Pre- and post-processing of German text using spaCy."""

    def __init__(self):
        self._holder = _SpacyModelHolder.get()

    @property
    def nlp(self):
        return self._holder.nlp

    # ── Pre-processing ──

    def clean_text(self, text: str) -> str:
        """Normalize whitespace and strip invisible characters."""
        # Normalize Unicode to NFC (composed form)
        text = unicodedata.normalize('NFC', text)
        # Replace non-breaking spaces and other Unicode whitespace with regular space
        text = re.sub(r'[\u00a0\u2000-\u200b\u202f\u205f\u3000]', ' ', text)
        # Collapse multiple spaces (but preserve newlines)
        text = re.sub(r'[^\S\n]+', ' ', text)
        # Strip leading/trailing whitespace per line
        text = '\n'.join(line.strip() for line in text.splitlines())
        return text.strip()

    def make_doc(self, text: str):
        """Create a spaCy Doc from text."""
        return self.nlp(text)

    def split_sentences(self, text: str) -> list[SentenceSpan]:
        """Split text into sentences, preserving character offsets into the original text."""
        doc = self.nlp(text)
        sentences = []
        for sent in doc.sents:
            sentences.append(SentenceSpan(
                text=sent.text,
                start_offset=sent.start_char,
                end_offset=sent.end_char,
            ))
        return sentences

    # ── Token analysis ──

    def analyze_token_at_offset(self, doc, char_offset: int) -> TokenInfo | None:
        """Return linguistic info for the token at a given character offset."""
        for token in doc:
            if token.idx <= char_offset < token.idx + len(token.text):
                return TokenInfo(
                    text=token.text,
                    pos=token.pos_,
                    morph=token.morph.to_dict(),
                    dep=token.dep_,
                    is_entity=token.ent_type_ != '',
                    entity_label=token.ent_type_,
                )
        return None

    # ── Post-processing: enhanced categorization ──

    def categorize_error(
        self,
        original_text: str,
        lt_category: str,
        lt_rule_id: str,
        doc,
        start_offset: int,
    ) -> str:
        """
        Override LanguageTool's category using spaCy POS/morphology when it
        provides a more specific classification — especially for German learner
        errors that LanguageTool lumps into GRAMMAR or OTHER.
        """
        token_info = self.analyze_token_at_offset(doc, start_offset)
        if token_info is None:
            return lt_category

        pos = token_info.pos
        morph = token_info.morph

        # Determiners (der/die/das/ein/eine/…) → ARTICLE
        if pos == 'DET':
            return DetectedError.Category.ARTICLE

        # Adpositions (in/an/auf/mit/…) → PREPOSITION
        if pos == 'ADP':
            return DetectedError.Category.PREPOSITION

        # Verbs or tokens with tense morphology → VERB_TENSE
        if pos in ('VERB', 'AUX'):
            return DetectedError.Category.VERB_TENSE
        if morph.get('Tense') or morph.get('VerbForm'):
            return DetectedError.Category.VERB_TENSE

        # If LanguageTool already gave a specific category, keep it
        return lt_category

    # ── Post-processing: error context extraction ──

    def extract_error_context(
        self,
        doc,
        start_offset: int,
        end_offset: int,
    ) -> dict:
        """
        Return surrounding linguistic context for the error span — useful for
        analytics and future ML-based improvements.
        """
        context: dict = {
            'tokens': [],
            'entities': [],
        }

        # Collect tokens that overlap [start_offset, end_offset)
        error_tokens = []
        for token in doc:
            tok_start = token.idx
            tok_end = token.idx + len(token.text)
            if tok_end > start_offset and tok_start < end_offset:
                error_tokens.append(token)

        for token in error_tokens:
            context['tokens'].append({
                'text': token.text,
                'pos': token.pos_,
                'morph': token.morph.to_dict(),
                'dep': token.dep_,
                'head': token.head.text,
            })

        # Named entities overlapping the error span
        for ent in doc.ents:
            if ent.end_char > start_offset and ent.start_char < end_offset:
                context['entities'].append({
                    'text': ent.text,
                    'label': ent.label_,
                })

        # One-token window before and after for dependency context
        if error_tokens:
            first_i = error_tokens[0].i
            last_i = error_tokens[-1].i
            if first_i > 0:
                prev = doc[first_i - 1]
                context['prev_token'] = {'text': prev.text, 'pos': prev.pos_}
            if last_i < len(doc) - 1:
                nxt = doc[last_i + 1]
                context['next_token'] = {'text': nxt.text, 'pos': nxt.pos_}

        return context

    def get_pos_tag(self, doc, start_offset: int) -> str:
        """Return the POS tag for the token at start_offset, or empty string."""
        token_info = self.analyze_token_at_offset(doc, start_offset)
        return token_info.pos if token_info else ''
