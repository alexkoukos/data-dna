"""X9: source-code fingerprints (winnowing) on top of the YARA rules.

YARA finds code by words it already knows. This finds code it has been shown: a registered file
is turned into a set of hashes that survive renaming variables, changing spacing and deleting
comments, so a pasted copy is caught even after a light disguise. Pure Python, no model.

Winnowing (Schleimer, Wilkerson, Aiken 2003): hash every k-gram of tokens, keep the smallest
hash in each window of w. Two texts that share a run of at least k+w-1 tokens share a hash.
"""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from brain.detection.patterns import Finding

K = 5  # tokens per k-gram
W = 4  # window of k-grams
MIN_TOKENS = 40  # shorter snippets are too small to fingerprint reliably
THRESHOLD = 0.5  # share of the registered file's fingerprints found in the text
_TOKEN = re.compile(r"[A-Za-z_]\w*|\d+(?:\.\d+)?|==|!=|<=|>=|->|=>|\S")
_COMMENT = re.compile(r"#[^\n]*|//[^\n]*|/\*.*?\*/", re.S)
_KEYWORDS = frozenset(
    [
        "def",
        "class",
        "return",
        "if",
        "elif",
        "else",
        "for",
        "while",
        "in",
        "not",
        "and",
        "or",
        "import",
        "from",
        "as",
        "try",
        "except",
        "finally",
        "with",
        "function",
        "const",
        "let",
        "var",
        "new",
        "this",
        "self",
        "null",
        "None",
        "True",
        "False",
        "true",
        "false",
        "int",
        "str",
        "float",
        "void",
        "public",
        "private",
        "static",
        "final",
        "break",
        "continue",
        "pass",
        "lambda",
        "yield",
        "raise",
        "throw",
        "catch",
    ]
)


def tokens(code: str) -> list[str]:
    """Words become ID (unless a language keyword), numbers become NUM, comments are dropped."""
    out: list[str] = []
    for tok in _TOKEN.findall(_COMMENT.sub(" ", code)):
        if tok[0].isdigit():
            out.append("NUM")
        elif tok[0].isalpha() or tok[0] == "_":
            out.append(tok if tok in _KEYWORDS else "ID")
        else:
            out.append(tok)
    return out


def fingerprints(code: str) -> set[int]:
    toks = tokens(code)
    if len(toks) < K:
        return set()
    grams = [
        int.from_bytes(hashlib.blake2b(" ".join(toks[i : i + K]).encode(), digest_size=8).digest())
        for i in range(len(toks) - K + 1)
    ]
    if len(grams) <= W:
        return {min(grams)}
    return {min(grams[i : i + W]) for i in range(len(grams) - W + 1)}


@dataclass(frozen=True)
class CodeMatch:
    name: str
    score: float


class CodeIndex:
    def __init__(self) -> None:
        self._files: dict[str, set[int]] = {}

    def __len__(self) -> int:
        return len(self._files)

    def add(self, name: str, code: str) -> bool:
        fp = fingerprints(code)
        if len(tokens(code)) < MIN_TOKENS or not fp:
            return False
        self._files[name] = fp
        return True

    def load_dir(self, path: Path) -> int:
        added = 0
        if path.is_dir():
            for f in sorted(path.iterdir()):
                if f.is_file() and f.suffix in {".py", ".js", ".ts", ".java", ".go", ".c", ".cs"}:
                    added += self.add(f.name, f.read_text(encoding="utf-8", errors="replace"))
        return added

    def match(self, text: str) -> list[CodeMatch]:
        if not self._files or len(tokens(text)) < MIN_TOKENS:
            return []
        seen = fingerprints(text)
        out = []
        for name, fp in self._files.items():
            score = len(fp & seen) / len(fp)
            if score >= THRESHOLD:
                out.append(CodeMatch(name, round(score, 2)))
        return sorted(out, key=lambda m: -m.score)

    def find(self, text: str) -> list[Finding]:
        """A Finding over the whole text, in the `source_code` category (policy: warn)."""
        hits = self.match(text)
        if not hits:
            return []
        return [
            Finding(
                entity=f"code:{hits[0].name}",
                category="source_code",
                start=0,
                end=len(text),
                value=text,
            )
        ]
