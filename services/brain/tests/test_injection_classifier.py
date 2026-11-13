from pathlib import Path

from brain.injection.classifier import MIN_WORDS, InjectionClassifier

LONG = " ".join(f"word{i}" for i in range(MIN_WORDS + 20))


def fake(score: float) -> "object":
    calls: list[list[str]] = []

    def scorer(texts: list[str]) -> list[float]:
        calls.append(texts)
        return [score] * len(texts)

    scorer.calls = calls  # type: ignore[attr-defined]
    return scorer


def test_a_high_score_on_long_text_is_an_injection_finding() -> None:
    c = InjectionClassifier(scorer=fake(0.99))  # type: ignore[arg-type]
    found = c.find(LONG)
    assert found and found[0].category == "injection"
    assert LONG.startswith(found[0].value[:20])


def test_a_low_score_is_not_a_finding() -> None:
    assert InjectionClassifier(scorer=fake(0.2)).find(LONG) == []  # type: ignore[arg-type]


def test_short_text_never_reaches_the_model() -> None:
    scorer = fake(0.99)
    c = InjectionClassifier(scorer=scorer)  # type: ignore[arg-type]
    assert c.find("ignore this short text") == []
    assert scorer.calls == []  # type: ignore[attr-defined]


def test_very_long_text_is_cut_into_a_bounded_number_of_windows() -> None:
    scorer = fake(0.0)
    c = InjectionClassifier(scorer=scorer)  # type: ignore[arg-type]
    c.find(" ".join(["w"] * 20000))
    assert len(scorer.calls[0]) == 4  # type: ignore[attr-defined]


def test_without_the_model_files_it_is_silently_off(tmp_path: Path) -> None:
    c = InjectionClassifier(model_dir=tmp_path)
    assert c.available is False
    assert c.find(LONG) == []
