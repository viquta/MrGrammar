from __future__ import annotations

from feedback.models import DetectedError


DISPLAY_GROUP_LABELS = {
    'verb_phrase': 'Verb Phrase',
    'noun_phrase': 'Noun Phrase',
    'adjective': 'Adjective',
    'spelling_word_choice': 'Spelling / Word Choice',
    'syntax': 'Syntax',
}


def derive_display_group(error: DetectedError) -> str:
    rule_id = (error.languagetool_rule_id or '').upper()
    pos_tag = (error.spacy_pos_tag or '').upper()

    if error.error_category == DetectedError.Category.SPELLING:
        return 'spelling_word_choice'

    if any(token in rule_id for token in {
        'HAUPTSATZ',
        'NEBENSATZ',
        'WORD_ORDER',
        'PUNCT',
        'COMMA',
        'CLAUSE',
        'SENTENCE',
    }):
        return 'syntax'

    if pos_tag in {'VERB', 'AUX'} or error.error_category == DetectedError.Category.VERB_TENSE:
        return 'verb_phrase'

    if pos_tag == 'ADJ':
        return 'adjective'

    if error.error_category in {
        DetectedError.Category.ARTICLE,
        DetectedError.Category.PREPOSITION,
    }:
        return 'noun_phrase'

    if pos_tag in {'DET', 'NOUN', 'PROPN', 'PRON'}:
        return 'noun_phrase'

    if error.error_category in {
        DetectedError.Category.GRAMMAR,
        DetectedError.Category.PUNCTUATION,
        DetectedError.Category.OTHER,
    }:
        return 'syntax'

    return 'noun_phrase'


def get_display_label(group: str) -> str:
    return DISPLAY_GROUP_LABELS.get(group, 'Syntax')