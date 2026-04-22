import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mrgrammar.settings')

import django
from django.conf import settings


django.setup()

from nlp.spacy_processor import SpacyTextProcessor


EXAMPLE_TEXT = (
    'Heute früh habe ich mein Tochter aufgewacht mit ein Lied.\n'
    'Sie wolte erst nicht wachen, also habe ich gesagd dass das\n'
    'ihre Mutter bald kommt mit Bobby, unsere Hund. Und ja, der\n'
    'Mamma von meiner Tochter kommt gerade und wir haben sie\n'
    'aufgewacht mit ein Spiel. Diese Spiel heißt: "finde die\n'
    'Kartoffel." Es ist ein kleines Kitzel am die finger am Fußen\n'
    '(ich weiß nicht wie sie heißen).'
)


def print_sentences(processor: SpacyTextProcessor, text: str) -> None:
    print('Sentences:')
    for index, sentence in enumerate(processor.split_sentences(text), start=1):
        print(
            f'  {index}. [{sentence.start_offset}:{sentence.end_offset}] '
            f'{sentence.text!r}'
        )


def print_tokens(doc) -> None:
    print('\nTokens:')
    for token in doc:
        if token.is_space:
            continue
        print(
            f'  idx={token.idx:<3} text={token.text!r:<14} '
            f'pos={token.pos_:<6} dep={token.dep_:<10} lemma={token.lemma_!r}'
        )


def main() -> None:
    processor = SpacyTextProcessor()
    try:
        doc = processor.make_doc(EXAMPLE_TEXT)
    except OSError:
        model_name = settings.MRGRAMMAR['SPACY_MODEL']
        print(f"spaCy model {model_name!r} is not installed in this local environment.")
        print('Install it with:')
        print(
            f'  /Users/victor/Documents/GitHub/MrGrammar/.venv/bin/python '
            f'-m spacy download {model_name}'
        )
        print('The Docker backend installs this model automatically, but your local .venv does not have it yet.')
        raise SystemExit(1)

    print('Point 3 demo: ErrorDetectionService builds one spaCy doc for the full submission text.')
    print(f'Characters: {len(EXAMPLE_TEXT)}')
    print(f'Tokens: {len([token for token in doc if not token.is_space])}')
    print_sentences(processor, EXAMPLE_TEXT)
    print_tokens(doc)


if __name__ == '__main__':
    main()


"""results:
(.venv) ) victor@MacBook-Air-victor MrGrammar % /Users/victor/Documents/GitHub/MrGrammar/.venv/bin/python test.py
Point 3 demo: ErrorDetectionService builds one spaCy doc for the full submission text.
Characters: 381
Tokens: 81
Sentences:
  1. [0:58] 'Heute früh habe ich mein Tochter aufgewacht mit ein Lied.\n'
  2. [58:163] 'Sie wolte erst nicht wachen, also habe ich gesagd dass das\nihre Mutter bald kommt mit Bobby, unsere Hund.'
  3. [164:257] 'Und ja, der\nMamma von meiner Tochter kommt gerade und wir haben sie\naufgewacht mit ein Spiel.'
  4. [258:299] 'Diese Spiel heißt: "finde die\nKartoffel."'
  5. [300:381] 'Es ist ein kleines Kitzel am die finger am Fußen\n(ich weiß nicht wie sie heißen).'

Tokens:
  idx=0   text='Heute'        pos=ADV    dep=mo         lemma='heute'
  idx=6   text='früh'         pos=ADV    dep=mo         lemma='früh'
  idx=11  text='habe'         pos=AUX    dep=ROOT       lemma='haben'
  idx=16  text='ich'          pos=PRON   dep=sb         lemma='ich'
  idx=20  text='mein'         pos=DET    dep=nk         lemma='mein'
  idx=25  text='Tochter'      pos=NOUN   dep=sb         lemma='Tochter'
  idx=33  text='aufgewacht'   pos=VERB   dep=oc         lemma='aufgewachen'
  idx=44  text='mit'          pos=ADP    dep=mo         lemma='mit'
  idx=48  text='ein'          pos=DET    dep=nk         lemma='ein'
  idx=52  text='Lied'         pos=NOUN   dep=nk         lemma='Lied'
  idx=56  text='.'            pos=PUNCT  dep=punct      lemma='--'
  idx=58  text='Sie'          pos=PRON   dep=sb         lemma='sie'
  idx=62  text='wolte'        pos=VERB   dep=ROOT       lemma='wolten'
  idx=68  text='erst'         pos=ADV    dep=mo         lemma='erst'
  idx=73  text='nicht'        pos=PART   dep=ng         lemma='nicht'
  idx=79  text='wachen'       pos=VERB   dep=oc         lemma='wachen'
  idx=85  text=','            pos=PUNCT  dep=punct      lemma='--'
  idx=87  text='also'         pos=ADV    dep=mo         lemma='also'
  idx=92  text='habe'         pos=AUX    dep=cj         lemma='haben'
  idx=97  text='ich'          pos=PRON   dep=sb         lemma='ich'
  idx=101 text='gesagd'       pos=VERB   dep=mo         lemma='gesagd'
  idx=108 text='dass'         pos=SCONJ  dep=mo         lemma='dass'
  idx=113 text='das'          pos=DET    dep=nk         lemma='der'
  idx=117 text='ihre'         pos=DET    dep=nk         lemma='ihr'
  idx=122 text='Mutter'       pos=NOUN   dep=sb         lemma='Mutter'
  idx=129 text='bald'         pos=ADV    dep=mo         lemma='bald'
  idx=134 text='kommt'        pos=VERB   dep=oc         lemma='kommen'
  idx=140 text='mit'          pos=ADP    dep=mo         lemma='mit'
  idx=144 text='Bobby'        pos=PROPN  dep=nk         lemma='Bobby'
  idx=149 text=','            pos=PUNCT  dep=punct      lemma='--'
  idx=151 text='unsere'       pos=DET    dep=nk         lemma='unser'
  idx=158 text='Hund'         pos=NOUN   dep=sb         lemma='Hund'
  idx=162 text='.'            pos=PUNCT  dep=punct      lemma='--'
  idx=164 text='Und'          pos=CCONJ  dep=ju         lemma='und'
  idx=168 text='ja'           pos=PART   dep=mo         lemma='ja'
  idx=170 text=','            pos=PUNCT  dep=punct      lemma='--'
  idx=172 text='der'          pos=DET    dep=nk         lemma='der'
  idx=176 text='Mamma'        pos=PROPN  dep=sb         lemma='Mamma'
  idx=182 text='von'          pos=ADP    dep=pg         lemma='von'
  idx=186 text='meiner'       pos=DET    dep=nk         lemma='mein'
  idx=193 text='Tochter'      pos=NOUN   dep=nk         lemma='Tochter'
  idx=201 text='kommt'        pos=VERB   dep=ROOT       lemma='kommen'
  idx=207 text='gerade'       pos=ADV    dep=mo         lemma='gerade'
  idx=214 text='und'          pos=CCONJ  dep=cd         lemma='und'
  idx=218 text='wir'          pos=PRON   dep=sb         lemma='wir'
  idx=222 text='haben'        pos=AUX    dep=cj         lemma='haben'
  idx=228 text='sie'          pos=PRON   dep=oa         lemma='sie'
  idx=232 text='aufgewacht'   pos=VERB   dep=oc         lemma='aufwachen'
  idx=243 text='mit'          pos=ADP    dep=mo         lemma='mit'
  idx=247 text='ein'          pos=DET    dep=nk         lemma='ein'
  idx=251 text='Spiel'        pos=NOUN   dep=nk         lemma='Spiel'
  idx=256 text='.'            pos=PUNCT  dep=punct      lemma='--'
  idx=258 text='Diese'        pos=DET    dep=nk         lemma='dieser'
  idx=264 text='Spiel'        pos=NOUN   dep=sb         lemma='Spiel'
  idx=270 text='heißt'        pos=VERB   dep=ROOT       lemma='heißen'
  idx=275 text=':'            pos=PUNCT  dep=punct      lemma='--'
  idx=277 text='"'            pos=PUNCT  dep=punct      lemma='--'
  idx=278 text='finde'        pos=VERB   dep=oc         lemma='finden'
  idx=284 text='die'          pos=DET    dep=nk         lemma='der'
  idx=288 text='Kartoffel'    pos=NOUN   dep=sb         lemma='Kartoffel'
  idx=297 text='.'            pos=PUNCT  dep=punct      lemma='--'
  idx=298 text='"'            pos=PUNCT  dep=punct      lemma='--'
  idx=300 text='Es'           pos=PRON   dep=sb         lemma='es'
  idx=303 text='ist'          pos=AUX    dep=ROOT       lemma='sein'
  idx=307 text='ein'          pos=DET    dep=nk         lemma='ein'
  idx=311 text='kleines'      pos=ADJ    dep=nk         lemma='klein'
  idx=319 text='Kitzel'       pos=NOUN   dep=pd         lemma='Kitzel'
  idx=326 text='am'           pos=ADP    dep=mnr        lemma='an'
  idx=329 text='die'          pos=DET    dep=nk         lemma='der'
  idx=333 text='finger'       pos=NOUN   dep=nk         lemma='Finger'
  idx=340 text='am'           pos=ADP    dep=mnr        lemma='an'
  idx=343 text='Fußen'        pos=NOUN   dep=nk         lemma='Fuße'
  idx=349 text='('            pos=PUNCT  dep=punct      lemma='--'
  idx=350 text='ich'          pos=PRON   dep=sb         lemma='ich'
  idx=354 text='weiß'         pos=VERB   dep=par        lemma='wissen'
  idx=359 text='nicht'        pos=PART   dep=ng         lemma='nicht'
  idx=365 text='wie'          pos=ADP    dep=cm         lemma='wie'
  idx=369 text='sie'          pos=PRON   dep=sb         lemma='sie'
  idx=373 text='heißen'       pos=VERB   dep=oc         lemma='heißen'
  idx=379 text=')'            pos=PUNCT  dep=punct      lemma='--'
  idx=380 text='.'            pos=PUNCT  dep=punct      lemma='--'
((.venv) ) victor@MacBook-Air-victor MrGrammar % 
 """