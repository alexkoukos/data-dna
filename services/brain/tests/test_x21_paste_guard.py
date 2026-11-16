import importlib.util
import urllib.error
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "paste_guard", Path(__file__).resolve().parents[3] / "tools" / "paste_guard.py"
)
assert spec and spec.loader
pg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pg)


def run(result: dict, auto: bool = False, answer: bool = True) -> tuple[str, list[str], list[str]]:
    said: list[str] = []
    written: list[str] = []
    out = pg.check_once(
        "some text",
        "http://x",
        auto,
        lambda q: answer,
        said.append,
        inspect_fn=lambda u, t: result,
        write=written.append,
    )
    return out, said, written


MASK = {
    "decision": "mask",
    "reasons": ["Contains iban"],
    "masked_messages": [{"role": "user", "content": "Pay [IBAN_1]"}],
}


def test_clean_text_and_empty_text_do_nothing() -> None:
    assert run({"decision": "allow"})[0] == "ok"
    assert pg.check_once("  ", "http://x", False, lambda q: True, print) == "empty"


def test_mask_offers_the_masked_text_and_replaces_when_accepted() -> None:
    out, said, written = run(MASK)
    assert out == "masked" and written == ["Pay [IBAN_1]"]
    assert "Contains iban" in said[0]


def test_declining_keeps_the_clipboard() -> None:
    out, _, written = run(MASK, answer=False)
    assert out == "kept" and written == []


def test_auto_replaces_without_asking() -> None:
    out, _, written = run(MASK, auto=True, answer=False)
    assert out == "masked" and written


def test_warn_uses_the_suggested_rewrite() -> None:
    out, _, written = run({"decision": "warn", "reasons": ["x"], "suggested_rewrite": "Safe"})
    assert out == "masked" and written == ["Safe"]


def test_block_is_flagged_and_never_replaced() -> None:
    out, said, written = run({"decision": "block", "reasons": ["Injection"]})
    assert out == "flagged" and written == [] and "Do not paste" in said[-1]


def test_an_unreachable_brain_says_so_and_changes_nothing() -> None:
    said: list[str] = []

    def down(url: str, text: str) -> dict:
        raise urllib.error.URLError("refused")

    out = pg.check_once("x", "http://x", True, lambda q: True, said.append, inspect_fn=down)
    assert out == "offline" and "make up" in said[0]
