# PROGRESS: handoff log

Newest entry at the top. Every session ends with a new entry (the `/handoff` command writes it). The next person continues from the top entry alone.

Template:

```
## YYYY-MM-DD HH:MM, <name>, task <ID>
**Done:** what now works (and how to see it)
**State:** branch, PR link, CI green or red, anything half-done
**Next step:** the exact next action, specific enough to start without asking
**Problems / decisions needed:**
**Files touched:**
```

---

## 2026-11-13 15:30, Alexandros, task S1
**Done:** `make setup` and `make up` run on macOS (OrbStack). Only fix needed: web healthcheck used `localhost`, which resolves to IPv6 in Alpine while nginx listens on IPv4, so the container stayed unhealthy. Now uses `127.0.0.1`. Verified: http://localhost:3000 returns 200, brain on :8001 healthy, `make check` green. Repo created private at github.com/alexkoukos/data-dna, `main` protected (PR + checks brain, web, smoke, secrets).
**State:** branch `task/S1-make-up`, PR open. CI smoke on GitHub not yet seen.
**Next step:** Confirm CI green on the PR, merge, then add the three collaborators (need their GitHub usernames), then task G1.
**Problems / decisions needed:** Collaborators not added yet.
**Files touched:** web/Dockerfile, PROGRESS.md, TASKS.md

---

## 2026-11-13 16:00, Alexandros (scaffold), task S0
**Done:** Repo skeleton. Locked dependencies for brain (`uv.lock`) and web (`package-lock.json`). Brain has a working `/healthz` and `/v1/inspect` that validates AFM, AMKA, IBAN, cards and secrets by checksum, normalises evasion tricks (invisible characters, spaced digits, base64), masks findings and applies the policy precedence. 19 brain tests and 2 web tests pass; ruff, mypy strict, oxlint, prettier clean. Data templates and `make validate` for the team's prompts, AI tools and org files. CI workflow (lint, types, tests, compose smoke with Playwright + axe, arm64 build, gitleaks). Devcontainer for identical environments.
**State:** `main`, first commit. Docker images were NOT built yet (no Docker daemon where the scaffold was made).
**Next step:** On a real machine: `make setup`, then `make up`, open http://localhost:3000 and http://localhost:8001/docs. Fix anything in the Dockerfiles that fails, then do task G1.
**Problems / decisions needed:** Product name. LiteLLM image tag to pin (G1). llama.cpp vs Ollama decided Sat 14 by measurement (L1).
**Files touched:** everything.
