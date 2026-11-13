---
description: Start a work session: sync, read the handoff, check tools, pick the next task
argument-hint: "[your name]"
---
You are starting a work session for $ARGUMENTS on this repo.

1. Run `git checkout main && git pull`.
2. Read `CLAUDE.md`, the newest entry at the top of `PROGRESS.md`, and `TASKS.md`.
3. Run `make doctor`. If anything is MISSING, explain in simple Greek how to install it and stop there.
4. If `services/brain/.venv` or `web/node_modules` is missing, run `make setup`.
5. Reply in simple Greek, short:
   - where the project stands (2 to 3 lines),
   - what the previous person left as the next step,
   - which open task in `TASKS.md` fits $ARGUMENTS (their name appears as owner), and ask which one to start.
Do not write code until the user picks a task.
