---
description: Claim and work on one task from TASKS.md
argument-hint: "<task ID, e.g. D3>"
---
Work on task $ARGUMENTS from `TASKS.md`.

1. Read the task line and the PRD sections it points to in `docs/PRD.md`.
2. Create a branch `task/$ARGUMENTS-<short-name>` from an up-to-date `main`.
3. Mark the task `[~] (<user name>)` in `TASKS.md`.
4. Plan in 3 to 6 steps and show the plan to the user before coding.
5. Build it with tests. Run `make check` before each commit. Keep commits small.
6. When the task's "Done when" is met, mark it `[x]`, then follow the end-of-session rules in `CLAUDE.md` (or run `/handoff`).
