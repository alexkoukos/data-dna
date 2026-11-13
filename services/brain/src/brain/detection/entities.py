"""People, emails, phones (Presidio + spaCy, English and Greek) and client names (aho-corasick).

Both return the same `Finding` the pattern checks return, so masking and policy treat them alike.
Presidio and the spaCy models load once, on first use or at start-up through `warm_up()`.
"""

import logging
import re
import threading
import unicodedata
from collections.abc import Iterable
from typing import Any

import ahocorasick

from brain.detection.patterns import Finding

log = logging.getLogger(__name__)

_GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
_LATIN = re.compile(r"[A-Za-z]")
# Greek mobile numbers (69xxxxxxxx) and any number with the +30 prefix, which Presidio scores low.
_GREEK_PHONE = re.compile(
    r"(?<![\w+])(?:\+30[ .-]?)?(?:69\d{2}[ .-]?\d{6}|(?<=\+30)[ .-]?2\d{9})(?!\d)"
)
_ENTITY_NAMES = {"PERSON": "PERSON", "EMAIL_ADDRESS": "EMAIL", "PHONE_NUMBER": "PHONE"}
_MIN_SCORE = {"PERSON": 0.6, "EMAIL_ADDRESS": 0.5, "PHONE_NUMBER": 0.35}


def _languages(text: str) -> list[str]:
    """Run the Greek model on Greek text and the English one on Latin text (both if mixed)."""
    langs = []
    if _LATIN.search(text):
        langs.append("en")
    if _GREEK.search(text):
        langs.append("el")
    return langs


class EntityDetector:
    def __init__(self) -> None:
        self._analyzer: Any = None
        self._lock = threading.Lock()

    def warm_up(self) -> None:
        self._load()

    def _load(self) -> Any:
        with self._lock:
            if self._analyzer is None:
                from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
                from presidio_analyzer.nlp_engine import NlpEngineProvider

                config = {
                    "nlp_engine_name": "spacy",
                    "models": [
                        {"lang_code": "en", "model_name": "en_core_web_sm"},
                        {"lang_code": "el", "model_name": "el_core_news_sm"},
                    ],
                }
                nlp = NlpEngineProvider(nlp_configuration=config).create_engine()
                registry = RecognizerRegistry(supported_languages=["en", "el"])
                registry.load_predefined_recognizers(languages=["en", "el"], nlp_engine=nlp)
                self._analyzer = AnalyzerEngine(
                    nlp_engine=nlp, registry=registry, supported_languages=["en", "el"]
                )
                log.info("Entity detector ready (en, el)")
            return self._analyzer

    def find(self, text: str) -> list[Finding]:
        found: list[Finding] = []
        if text.strip():
            analyzer = self._load()
            for lang in _languages(text):
                for r in analyzer.analyze(
                    text=text, language=lang, entities=list(_ENTITY_NAMES), score_threshold=0.3
                ):
                    if (
                        r.score >= _MIN_SCORE[r.entity_type]
                        and not _stray_word(text, r)
                        and not _cyrillic_name(text, r)
                    ):
                        found.append(
                            Finding(
                                _ENTITY_NAMES[r.entity_type],
                                "person_email_phone",
                                r.start,
                                r.end,
                                text[r.start : r.end],
                            )
                        )
        for m in _GREEK_PHONE.finditer(text):
            found.append(Finding("PHONE", "person_email_phone", m.start(), m.end(), m.group(0)))
        return _merge(found)


_CYRILLIC = re.compile("[Ѐ-ӿ]")


def _cyrillic_name(text: str, r: Any) -> bool:
    """Neither language model reads Russian: it calls "Доброе утро" a person. Skip those."""
    return r.entity_type == "PERSON" and bool(_CYRILLIC.search(text[r.start : r.end]))


def _stray_word(text: str, r: Any) -> bool:
    """A lone word that opens a sentence ("Summarise:", "Write") is a verb, not a name."""
    if r.entity_type != "PERSON" or " " in text[r.start : r.end].strip():
        return False
    before = text[: r.start].rstrip()
    return not before or before[-1] in ".!?:;\n"


def _merge(items: list[Finding]) -> list[Finding]:
    """Same text found twice (two languages, or a phone rule too): keep the longest."""
    items.sort(key=lambda f: (f.start, -(f.end - f.start)))
    out: list[Finding] = []
    for f in items:
        if out and f.start < out[-1].end:
            continue
        out.append(f)
    return out


def _fold(text: str) -> str:
    """Lower case, no accents, one output character per input character (offsets stay valid)."""
    out = []
    for ch in text:
        base = unicodedata.normalize("NFD", ch)[0].lower()
        out.append("σ" if base == "ς" else base)
    return "".join(out)


class ClientMatcher:
    """Case-insensitive, accent-insensitive whole-word match against client names and aliases."""

    def __init__(self, names: Iterable[str]) -> None:
        self._auto = ahocorasick.Automaton()
        count = 0
        for name in names:
            key = _fold(name.strip())
            if len(key) >= 3:
                self._auto.add_word(key, key)
                count += 1
        self._empty = count == 0
        if not self._empty:
            self._auto.make_automaton()

    def find(self, text: str) -> list[Finding]:
        if self._empty or not text:
            return []
        folded = _fold(text)
        found: list[Finding] = []
        for end, key in self._auto.iter(folded):
            start = end - len(key) + 1
            before = folded[start - 1] if start > 0 else " "
            after = folded[end + 1] if end + 1 < len(folded) else " "
            if before.isalnum() or after.isalnum():
                continue
            found.append(Finding("CLIENT", "client_name", start, end + 1, text[start : end + 1]))
        return _merge(found)
