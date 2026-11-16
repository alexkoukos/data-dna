from pathlib import Path

import pytest

from brain.detection.code_fingerprint import CodeIndex, fingerprints, tokens

DATA = Path(__file__).resolve().parents[3] / "data" / "code"
ORIGINAL = (DATA / "pricing_engine.py").read_text()


@pytest.fixture
def index() -> CodeIndex:
    i = CodeIndex()
    assert i.load_dir(DATA) == 1
    return i


def test_tokens_ignore_names_numbers_and_comments() -> None:
    a = tokens("def f(x):  # note\n    return x + 1")
    b = tokens("def other_name(value):\n    return value + 99")
    assert a == b


def test_an_exact_copy_matches(index: CodeIndex) -> None:
    hits = index.match(ORIGINAL)
    assert hits and hits[0].name == "pricing_engine.py" and hits[0].score == 1.0


def test_renamed_reformatted_and_commented_copy_still_matches(index: CodeIndex) -> None:
    disguised = ORIGINAL.replace("subtotal", "running").replace("base_cost", "bc")
    disguised = disguised.replace("margin", "mrg").replace("tier", "level")
    disguised = "# totally my own code\n" + disguised.replace("\n    ", "\n        ")
    hits = index.match(disguised)
    assert hits and hits[0].score >= 0.9


def test_one_function_pasted_is_caught(index: CodeIndex) -> None:
    start = ORIGINAL.index("def quote_price")
    end = ORIGINAL.index("def risk_score")
    assert index.match(ORIGINAL[start:end])


def test_unrelated_code_and_prose_are_left_alone(index: CodeIndex) -> None:
    other = """
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

def is_palindrome(text):
    cleaned = [c.lower() for c in text if c.isalnum()]
    return cleaned == cleaned[::-1]

def average(values):
    return sum(values) / len(values) if values else 0
"""
    assert index.match(other) == []
    assert index.match("Please summarise the quarterly meeting notes for the team. " * 10) == []


def test_finding_is_in_the_source_code_category(index: CodeIndex) -> None:
    f = index.find(ORIGINAL)
    assert f and f[0].category == "source_code" and f[0].entity == "code:pricing_engine.py"


def test_tiny_files_are_not_registered_and_empty_index_matches_nothing() -> None:
    i = CodeIndex()
    assert i.add("x.py", "a = 1") is False
    assert i.match(ORIGINAL) == [] and len(i) == 0
    assert fingerprints("a") == set()
