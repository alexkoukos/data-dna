"""X21: Paste guard. A small local program that watches the clipboard before you paste into an AI.

Not part of `docker compose`. Standard library only, so it runs with any Python 3.10+.

    python tools/paste_guard.py                 # ask before replacing the clipboard
    python tools/paste_guard.py --auto          # replace the clipboard with the masked text
    python tools/paste_guard.py --url http://localhost:8001 --once

When you copy something sensitive it calls the brain (`POST /v1/inspect`) and, if the answer is
mask or warn, offers the masked version. Nothing is stored; the text only goes to your own gateway.
Read-only on failure: if the brain cannot be reached it says so and leaves the clipboard alone.
"""

import argparse
import json
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable

DEFAULT_URL = "http://localhost:8001"


def read_clipboard() -> str:
    system = platform.system()
    if system == "Darwin":
        cmd = ["pbpaste"]
    elif system == "Windows":
        cmd = ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"]
    else:
        cmd = ["xclip", "-selection", "clipboard", "-o"]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=3, check=False).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def write_clipboard(text: str) -> None:
    system = platform.system()
    if system == "Darwin":
        cmd = ["pbcopy"]
    elif system == "Windows":
        cmd = ["clip"]
    else:
        cmd = ["xclip", "-selection", "clipboard"]
    subprocess.run(cmd, input=text, text=True, timeout=3, check=False)


def inspect(url: str, text: str, user: str = "paste-guard") -> dict:
    body = json.dumps(
        {"user_id": user, "team": "desktop", "messages": [{"role": "user", "content": text}]}
    ).encode()
    req = urllib.request.Request(
        url.rstrip("/") + "/v1/inspect", body, {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 (a URL the user chose)
        return json.load(resp)


def masked_text(result: dict) -> str | None:
    msgs = result.get("masked_messages") or []
    return msgs[-1]["content"] if msgs else result.get("suggested_rewrite")


def check_once(
    text: str,
    url: str,
    auto: bool,
    ask: Callable[[str], bool],
    say: Callable[[str], None],
    inspect_fn: Callable[[str, str], dict] = inspect,
    write: Callable[[str], None] = write_clipboard,
) -> str:
    """Returns what happened: 'empty', 'ok', 'offline', 'masked', 'kept' or 'flagged'."""
    if not text.strip():
        return "empty"
    try:
        result = inspect_fn(url, text)
    except (urllib.error.URLError, OSError, ValueError):
        say("Paste guard could not reach Pyli, so this was not checked. Start it with: make up")
        return "offline"
    decision = result.get("decision", "allow")
    if decision == "allow":
        return "ok"
    reasons = "; ".join(result.get("reasons", [])) or "sensitive content"
    say(f"Pyli says {decision.upper()}: {reasons}.")
    safe = masked_text(result)
    if decision in ("mask", "warn") and safe:
        if auto or ask("Replace the clipboard with the masked version?"):
            write(safe)
            say("Clipboard replaced with the masked version. Paste it instead.")
            return "masked"
        return "kept"
    say("Do not paste this into an AI tool. Use the company chat or remove the sensitive part.")
    return "flagged"


def _ask(question: str) -> bool:
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--url", default=DEFAULT_URL, help="Pyli brain URL")
    ap.add_argument("--auto", action="store_true", help="replace without asking")
    ap.add_argument("--once", action="store_true", help="check the clipboard once and exit")
    ap.add_argument("--interval", type=float, default=1.0, help="seconds between checks")
    args = ap.parse_args(argv)
    last = None
    print("Paste guard is watching the clipboard. Press Ctrl+C to stop.")
    try:
        while True:
            text = read_clipboard()
            if text != last:
                last = text
                outcome = check_once(text, args.url, args.auto, _ask, print)
                if outcome == "masked":
                    last = read_clipboard()
            if args.once:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
