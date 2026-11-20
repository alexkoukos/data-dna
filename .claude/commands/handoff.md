---
description: End the session cleanly so anyone can continue
---
The user is stopping (task done, end of day, or running out of tokens). Hand off now, even if work is unfinished.

1. Run `make check`. Do not hide failures; record them.
2. If code is half-done and breaks checks, either finish the smallest piece that makes them pass or move it behind a clearly named TODO, so the branch stays green when possible.
3. Commit (no Claude attribution lines), push the branch, open or update the PR, and show the user the PR link. The PR description says what was done, the current state, one concrete next step someone can start without asking, and open problems.
4. Tell the user in simple Greek: what is saved, and what to send the next person (the PR link).
