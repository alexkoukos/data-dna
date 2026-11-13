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

## 2026-11-13 23:00, Alexandros, task W1
**Done:** Company Chat at `/chat`. On first visit the page asks the brain for a personal key (`POST /v1/keys`, new, demo mode only, creates the team and key in LiteLLM) and keeps it in localStorage. Messages go through nginx `/gateway/` to the gateway. The gateway now sends `x-dna-decision` and `x-dna-reasons` headers, so each message shows an outcome chip with icon and text (Allowed, Masked, Answered locally, Warned, Blocked) and a "Why?" disclosure in plain words. Warn shows a card (Edit message is primary, Send anyway needs a reason and is sent as `X-DNA-Ack`, Cancel). Block shows the reasons and the approved alternative. Loading skeleton, empty state with three starter prompts, friendly errors with retry. Chips now have icons everywhere. Works at 390 px, no horizontal scroll, axe clean. Tests: 14 web unit tests, 2 new Playwright flows through the real stack, 5 new brain tests.
**State:** branch `task/W1-company-chat`, PR open. `make check` green; `make e2e` 6 passed against `make up`. No database change. Run `make up` again after pulling (nginx, compose env and gateway changed).
**Next step:** G2 streaming (the last open part of G2). Then W6 (axe and 390 px for every route as they get built) or W2 (Security overview).
**Problems / decisions needed:** (1) The PRD warn card has three actions: Send without it / Send anyway / Cancel. "Send without it" is replaced by "Edit message" because the brain does not return a masked text for warn. (2) Attach file and history sidebar are not built (file upload needs D4). (3) Each request sends only earlier turns that passed untouched, so a masked or warned message is never resent to the model in clear text. (4) The offline `demo-mock` model gives the same answer to everything; set `OPENAI_API_KEY` in `.env` for real answers. (5) `POST /v1/keys` has no login, so anyone who can reach the brain port can create keys; it is switched off when `DEMO_MODE=false`.
**Files touched:** web/src/{pages/ChatPage.tsx,components/*,lib/*,index.css,App.tsx,test/setup.ts}, web/nginx.conf, web/e2e/smoke.spec.ts, services/brain/src/brain/{keys.py,main.py,config.py,api/schemas.py}, services/brain/tests/test_keys.py, infra/gateway/{dna_inspect.py,dna_guardrail.py}, docker-compose.yml, TASKS.md, PROGRESS.md

---

## 2026-11-13 20:30, Alexandros, task P1
**Done:** Policies live in Postgres (`policies` table), seeded once from `services/brain/src/brain/policy/policies.yaml` at brain start (11 rows). `GET /v1/policies` lists them, `PUT /v1/policies` edits one (`scope` category or sensitivity, `key`, `action`, `updated_by`), validates with plain messages (422) and writes `audit_log`. The detection pipeline now uses the live policies (cached 5 s); with no database it falls back to the seed file, so detection never stops. Checked on real Postgres: edited iban to warn, `/v1/inspect` returned warn, audit row written, restored to mask.
**State:** branch `task/P1-policies`, PR open. `make check` green (53 brain tests, 96% coverage). No database change, so no `make reset` needed.
**Next step:** W1 Company Chat (`web/src/pages`). Policy editor UI is W5 (P1).
**Problems / decisions needed:** `PUT /v1/policies` has no login yet; anyone who can reach the brain port can edit. Roles come with the web login. Unit tests set `DATABASE_URL=""` in `conftest.py` so they never need Postgres.
**Files touched:** services/brain/src/brain/{main.py,detection/pipeline.py,api/schemas.py,db/engine.py,policy/store.py,policy/policies.yaml}, services/brain/tests/{conftest.py,test_policy_store.py}, TASKS.md, PROGRESS.md

---

## 2026-11-13 19:00, Alexandros, tasks G2 and G3
**Done:** Brain `POST /v1/inspect-output` (masks secrets and identifiers the model puts in an answer) and `POST /v1/unmask` (restores the user's own masked values, only for the same user, held in memory for 15 minutes). `/v1/inspect` now returns a `session_id` when it masks. The gateway guardrail runs both after the model answers: filter first, then unmask; if the brain is down the answer is withheld (503). Warn (409 + `X-DNA-Ack`) and block (403) responses are in place with reasons and an approved alternative. Config: guardrail mode is `[pre_call, post_call]` (with only `pre_call` the answer hook never runs). Extra offline models `demo-echo` and `demo-leaky` let tests prove unmask and output filtering without an OpenAI key.
**State:** branch `task/G2-unmask-output`, PR open. `make check` green (42 brain tests, 95% coverage). `make test-gateway` 6 live tests green.
**Next step:** G2 streaming: unmask chunk by chunk (hold back text after an unclosed `[`) and filter at the end; this is the only open part of G2. Then P1 (policies from DB) or W1 (Company Chat), whichever you pick.
**Problems / decisions needed:** Streaming answers currently pass through without unmask or filtering. Block cannot be triggered live until the injection check (D6, Stelios) exists; it is covered by a unit test. Output injection checks are also waiting for D6.
**Files touched:** services/brain/src/brain/{main.py,sessions.py,api/schemas.py}, infra/gateway/*, services/brain/tests/*, TASKS.md, PROGRESS.md

---

## 2026-11-13 17:00, Alexandros, task G1
**Done:** LiteLLM gateway (`ghcr.io/berriai/litellm:v1.109.1`) in compose on :4000. Custom guardrail `infra/gateway/dna_guardrail.py` calls `brain /v1/inspect` before every request: mask replaces the messages, warn returns 409 (the `X-DNA-Ack` header lets it through), block returns 403, local reroutes to model `local`. Fails closed with 503 if the brain is down. Virtual keys work (needs a team first: `POST /team/new`, then `/key/generate`). Offline model `demo-mock` answers without an OpenAI key. LiteLLM has its own database `litellm` (`infra/db/02-litellm.sql`, created on a fresh volume only, so run `make reset` once after pulling).
**State:** branch `task/G1-gateway`, PR open. `make check` green (30 brain tests, 94% coverage). `make test-gateway` (4 live tests through the OpenAI SDK, needs `make up`) green locally.
**Next step:** G3 (warn/block polish) and G2 (unmask + `/v1/inspect-output`). The brain has no `/v1/unmask` yet, so mask answers still show placeholders. Add `LITELLM_MASTER_KEY=sk-admin-change-me` to `.env.example` (compose has the default already).
**Problems / decisions needed:** Model `local` is not defined until L1 (Ollama), so a `local` decision currently fails. Key creation by the brain (`/v1/keys`) is not built yet.
**Files touched:** infra/gateway/*, infra/db/02-litellm.sql, infra/db/Dockerfile, docker-compose.yml, Makefile, services/brain/tests/test_gateway_*.py, TASKS.md, PROGRESS.md

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
