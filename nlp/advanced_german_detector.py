from __future__ import annotations

from feedback.models import DetectedError

from .spacy_processor import SpacyTextProcessor


class AdvancedGermanGrammarDetector:
    """Bounded German B1/B2 checks that complement LanguageTool."""

    SUPPORTED_LANGUAGES = {'de', 'de-DE', 'de-AT', 'de-CH'}
    SUBORDINATE_MARKERS = frozenset({
        'als', 'bevor', 'bis', 'dass', 'falls', 'nachdem', 'ob', 'obwohl',
        'seit', 'seitdem', 'sobald', 'sodass', 'sofern', 'waehrend', 'während',
        'weil', 'wenn',
    })
    WUERDE_FORMS = frozenset({'würde', 'würdest', 'würden', 'würdet'})
    FEMININE_ARTICLE_FIXES = {
        'ein': 'eine',
        'kein': 'keine',
        'mein': 'meine',
        'dein': 'deine',
        'sein': 'seine',
        'ihr': 'ihre',
        'unser': 'unsere',
        'euer': 'eure',
    }

    def __init__(self):
        self.processor = SpacyTextProcessor()

    def detect(self, text: str, language: str) -> list[dict]:
        if language not in self.SUPPORTED_LANGUAGES:
            return []

        doc = self.processor.make_doc(text)
        errors = []
        errors.extend(self._detect_subordinate_word_order(doc))
        errors.extend(self._detect_feminine_noun_phrase_agreement(doc))
        errors.extend(self._detect_wuerde_plus_infinitive(doc))
        return errors

    def _detect_subordinate_word_order(self, doc) -> list[dict]:
        errors = []
        for sent in doc.sents:
            sent_tokens = [token for token in sent if not token.is_space]
            lexical_tokens = [token for token in sent_tokens if not token.is_punct]
            if len(lexical_tokens) < 4:
                continue

            for marker in lexical_tokens:
                if marker.text.lower() not in self.SUBORDINATE_MARKERS:
                    continue

                clause_end_i = sent.end
                for token in sent_tokens:
                    if token.i <= marker.i:
                        continue
                    if token.is_punct and token.text == ',':
                        clause_end_i = token.i
                        break

                clause_tokens = [
                    token for token in lexical_tokens
                    if marker.i < token.i < clause_end_i
                ]
                if len(clause_tokens) < 3:
                    continue

                finite_verbs = [
                    token for token in clause_tokens
                    if token.pos_ in {'VERB', 'AUX'} and 'Fin' in token.morph.get('VerbForm')
                ]
                if not finite_verbs:
                    continue

                finite_verb = finite_verbs[0]
                last_token = clause_tokens[-1]
                if finite_verb == last_token:
                    continue

                trailing_content = [
                    token for token in clause_tokens
                    if token.i > finite_verb.i and token.pos_ not in {'PART', 'SCONJ', 'CCONJ'}
                ]
                if not trailing_content:
                    continue

                reordered = [token.text for token in clause_tokens if token != finite_verb]
                reordered.append(finite_verb.text)

                start_token = clause_tokens[0]
                end_token = clause_tokens[-1]
                errors.append({
                    'start_offset': start_token.idx,
                    'end_offset': end_token.idx + len(end_token.text),
                    'original_text': doc.text[start_token.idx:end_token.idx + len(end_token.text)],
                    'correct_solution': ' '.join(reordered),
                    'hint_text': (
                        f'Nach "{marker.text}" steht das finite Verb im Deutschen meist am Ende des Nebensatzes.'
                    ),
                    'error_category': DetectedError.Category.GRAMMAR,
                    'languagetool_rule_id': 'GERMAN_WORD_ORDER_SUBORDINATE',
                })
                break

        return errors

    def _detect_feminine_noun_phrase_agreement(self, doc) -> list[dict]:
        errors = []
        for token in doc:
            if token.pos_ != 'NOUN':
                continue

            gender = token.morph.get('Gender')
            number = token.morph.get('Number')
            if 'Fem' not in gender or 'Sing' not in number:
                continue

            determiner = next((child for child in token.lefts if child.pos_ == 'DET'), None)
            if determiner is not None:
                replacement = self.FEMININE_ARTICLE_FIXES.get(determiner.text.lower())
                if replacement:
                    errors.append({
                        'start_offset': determiner.idx,
                        'end_offset': determiner.idx + len(determiner.text),
                        'original_text': determiner.text,
                        'correct_solution': self._match_case(replacement, determiner.text),
                        'hint_text': 'Bei femininen Nomen im Singular braucht der Begleiter hier die feminine Form.',
                        'error_category': DetectedError.Category.ARTICLE,
                        'languagetool_rule_id': 'GERMAN_ARTICLE_FEMININE_NOUN_PHRASE',
                    })

            if determiner is None or determiner.text.lower() not in {'eine', 'keine', 'meine', 'deine', 'seine', 'ihre', 'unsere', 'eure'}:
                continue

            adjective = next(
                (
                    child for child in token.lefts
                    if child.pos_ in {'ADJ', 'ADV'} and child.dep_ == 'nk'
                ),
                None,
            )
            if adjective is None:
                continue
            if adjective.text.lower().endswith('e'):
                continue

            errors.append({
                'start_offset': adjective.idx,
                'end_offset': adjective.idx + len(adjective.text),
                'original_text': adjective.text,
                'correct_solution': f'{adjective.text}e',
                'hint_text': 'Nach einer femininen Singularform wie "eine" braucht das Adjektiv hier meist die Endung "-e".',
                'error_category': DetectedError.Category.GRAMMAR,
                'languagetool_rule_id': 'GERMAN_ADJECTIVE_ENDING_FEMININE',
            })

        return errors

    def _detect_wuerde_plus_infinitive(self, doc) -> list[dict]:
        errors = []
        for sent in doc.sents:
            tokens = [token for token in sent if not token.is_space and not token.is_punct]
            for index, token in enumerate(tokens[:-1]):
                if token.text.lower() not in self.WUERDE_FORMS:
                    continue

                verb = next((candidate for candidate in tokens[index + 1:] if candidate.pos_ in {'VERB', 'AUX'}), None)
                if verb is None:
                    continue

                lemma = (verb.lemma_ or '').strip()
                if not lemma or verb.text.lower() == lemma.lower():
                    continue

                errors.append({
                    'start_offset': verb.idx,
                    'end_offset': verb.idx + len(verb.text),
                    'original_text': verb.text,
                    'correct_solution': lemma,
                    'hint_text': 'Nach "würde" folgt in der Regel der Infinitiv.',
                    'error_category': DetectedError.Category.VERB_TENSE,
                    'languagetool_rule_id': 'GERMAN_VERB_WUERDE_INFINITIVE',
                })

        return errors

    def _match_case(self, replacement: str, original: str) -> str:
        if original[:1].isupper():
            return replacement.capitalize()
        return replacement