# CLAUDE.md: rules for Claude Code in this repo

This repo is shared by four people who hand work to each other, often mid-feature, when someone runs out of tokens. Your job is to keep the repo in a state where anyone can pick it up in five minutes.

## What we are building
Data DNA, an AI gateway for Netcompany Hackathon Athens 2026, Challenge 3 (Shadow AI protection and Data Protection). The full spec is `docs/PRD.md`. The plain-language version for the whole team is `docs/IDEA_AND_TEAM.md`. Read the PRD section you need before writing code; do not guess the design.

Deadline: Friday 20 Nov 2026, judged from the repo alone. If `docker compose up --build` fails on a judge's machine, the submission is void.

## Start of every session (the `/start` command does this)
1. `git pull` on `main`.
2. Read the newest entry at the top of `PROGRESS.md` and the task board `TASKS.md`.
3. Run `make doctor`. If something is missing, help the user install it before anything else.
4. Tell the user, in simple Greek, where the project stands and which task is next for them.

## While working
- One task from `TASKS.md` at a time. Mark it `[~] (name)` when you start.
- Work on a branch `task/<ID>-<short-name>` and open a PR into `main`. Never push directly to `main`.
- Small commits that each leave tests green.
- Before every commit: `make check`. Do not commit with failing checks; fix them or ask.
- Never break `docker compose up --build`. Any change to Dockerfiles, compose or dependencies needs a note in `PROGRESS.md` and, if possible, a real `make up` run.
- Dependencies: add with `uv add <pkg>` (in `services/brain`) or `npm install <pkg>` (in `web`) so the lock files update, and commit the lock files. Never install anything only on your machine.
- No secrets in code, tests, logs or commits. Keys live in `.env` only.
- No real personal data. Everything is synthetic (`data/`), generated or invented.
- Do not add Claude attribution to commits or PRs: no `Co-Authored-By`, no "Generated with Claude Code".
- Commit messages: English, imperative, short (`Add AMKA validator`).

## End of every session (the `/handoff` command does this)
When the task is done, or the user says they are stopping or running out of tokens:
1. `make check`. Note anything failing.
2. Add a new entry at the TOP of `PROGRESS.md` using its template: what was done, current state, exact next step, open problems, files touched.
3. Update `TASKS.md` statuses.
4. Commit, push the branch, open or update the PR, and give the user its link.
The next person must be able to continue from the PROGRESS entry alone.

## Code conventions
- Brain: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2. `ruff` and `mypy --strict` must pass. Tests in `services/brain/tests`, coverage at least 80%.
- Detection order is cheapest first (PRD section 9). Keep functions pure where possible; I/O at the edges.
- Web: React + TypeScript + Tailwind v4. Tokens are in `web/src/index.css` `@theme`; use only those. Presentational components in `src/components`, screens and data fetching in `src/pages`. Tests next to components (`*.test.tsx`).
- Every user-facing message says what happened and what to do next, in plain words.

## Frontend rules (apply to every screen)
Refactoring UI, Baranov's typography, Nielsen's 10 heuristics, Better Stories copy:
- One primary action per screen; secondary and tertiary styled down.
- Hierarchy with weight and color before size. Spacing from the scale; space between groups larger than within.
- Outcome states (Allowed, Masked, Warned, Answered locally, Blocked) always shown with text and icon, never color alone.
- WCAG AA contrast, visible keyboard focus, labels on every control, `aria-label` on icon buttons, touch targets at least 44 px.
- Works at 390 px wide. Loading (skeletons), empty, error and success states designed for every screen.

## Team learning rule
After finishing a feature with a user, ask them 3 "why" questions about the design, one at a time, and wait for their answer before revealing yours. Skip if they say skip.

## Commands
`make help` lists everything. Most used: `make setup`, `make up`, `make check`, `make test`, `make validate`, `make e2e`, `make down`.
