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

## 2026-11-13 18:00, Alexandros, tasks E4, S2 (partly), W4
**Done:**
- **E4 (PR #10):** live tests through the gateway for all five outcomes, each checking `x-dna-decision`. Local and block are triggered by remapping a category with `PUT /v1/policies` (restored after each test) because D3 and D6 do not exist yet. A mock `local` model was added to `infra/gateway/config.yaml` as a stand-in until L1. When D6/D3 land, switch those two tests to real triggers.
- **S2 (PR #11, still open task):** macOS Apple silicon measured from a fresh clone with no cache: build 72 s, healthy in 48 s, about 770 MB idle RAM. Written in README. **Linux and Windows WSL 2 are not run**: someone with those machines must run `docker compose up --build`, then add RAM and time to the README table.
- **W4:** `/connect` page. Gateway address and personal key (hidden until Show) with copy buttons, tabs for Python, JavaScript, curl and n8n, live status "Waiting for first request" then "Connected" (polls every 3 s). Claude Code and MCP tabs say "Not available yet" (G4 and M1 are P2). New brain endpoint `GET /v1/users/{id}/seen` (true once the gateway has checked a request for that user). No database change.
**State:** branches `task/E4-gateway-outcomes` (#10), `task/S2-platform-check` (#11), `task/W4-connect-page` (this PR). `make check` green (82 brain tests, 32 web tests); `make e2e` 17 passed against `make up`. E4 and W4 are done; S2 is `[~]`. R1: setup part of the README is written; the other sections belong to Konstantinos.
**Next step:** merge the three PRs, then pick W5 (Policies and Documents pages; `GET/PUT /v1/policies` exist), W3 (incident detail), A1 (preset questions) or N2 (sealed identity). Someone runs S2 on Linux and WSL. R4 freeze is Thu 19 Nov 20:00.
**Problems / decisions needed:** the gateway address on `/connect` is built from the page host plus port 4000, so it is right for local use and for a server that exposes port 4000. The seen check only knows users the brain has recorded, so a key created outside the demo flow shows "Waiting" until its first request.
**Files touched:** services/brain/src/brain/{main.py,api/schemas.py}, services/brain/tests/{test_dashboard_api.py,test_gateway_live.py}, infra/gateway/config.yaml, web/src/{pages/ConnectPage.tsx,pages/ConnectPage.test.tsx,components/CopyField.tsx,lib/snippets.ts,App.tsx}, web/e2e/smoke.spec.ts, README.md, TASKS.md, PROGRESS.md

---

## 2026-11-14 05:00, Alexandros, tasks O1, O2, W2, W6 and project summary
**Done (this entry):**
- **O1 seed:** the demo company is generated and loaded when the brain starts on an empty database (`services/brain/src/brain/seed/`). 200 users (Greek names, pseudonyms `u-xxxxxxxx`), 8 teams, 10 clients, 3 documents, 14 days of gateway counters, about 660 incidents, and the storyline (tool spike, API key paste, contract paste, salary questions, memo rebuilt over days). Deterministic: `--seed 42` plus the anchor date. CLI: `uv run python ../../scripts/gen_org.py` from `services/brain`, or `python -m brain.seed`.
- **O2 ingest:** Squid `access.log` and Zeek `dns.log` in real formats plus a DHCP-style `leases.csv` are written to the `logs` volume (`/var/dna/logs`). The ingest matches hosts and parent domains against the AI tool catalogue; DNS-only use counts once per user and day; gateway tools (domains ending `.local`) come from gateway counters, not logs.
- **Dashboard APIs:** `GET /v1/metrics`, `GET /v1/incidents` (decision and team filters, limit up to 100, offset), `GET /v1/inventory`. Real chat decisions are recorded too (`brain/records.py`): every non-allow becomes an incident (masked preview only, never the raw value), every check bumps `counters_daily`.
- **W2:** `/security` (Overview), `/security/tools` (AI tools, unapproved first, filter, 7-day sparkline), `/security/incidents` (filter by outcome, show more). Skeleton, empty and error states on each.
- **W6:** Playwright checks axe, no sideways scroll and 44 px touch targets on all 6 routes at 1280 px and 390 px (`web/e2e/smoke.spec.ts`, route list at the top).
**State:** everything is merged to `main` (PRs #1 to #8). `make check` green: 81 brain tests (94% coverage), 24 web tests. `make e2e` 16 passed against `make up`. CI green (brain, web, smoke, arm64, secrets). Branch protection on `main`: PR and the four checks required.
**Done so far (TASKS.md):** S0, S1, D0, G1, G2, G3, P1, O1, O2, W1, W2, W6.
**Next step (pick one):**
1. Alexandros P0: **E4** integration tests for all five outcomes through the gateway (block needs D6 to trigger live; use a unit-level block), **S2** platform check (Linux, Mac Apple silicon, Windows WSL; write RAM and first-start time in the README), **R1** README setup part, **R4** freeze Thu 19 Nov 20:00 and submit Fri 20 Nov by noon.
2. Alexandros P1: **W4** Connect page (key and URL with copy buttons, snippets, live status; `POST /v1/keys` already exists), **W5** Policies and Documents pages (`GET/PUT /v1/policies` exist), **W3** incident detail, **A1** analyst preset questions, **N2** sealed identity.
3. Stelios (not started): D1 Presidio, D2 YARA, D3 document registry (go/no-go Sat 14), D4 file upload, E1 `make eval`, then L1 local model, D6 injection (unblocks live block), D5, O3, N1, E2, E3.
4. Konstantinos and Vasilis (not started): T1 `org.yaml`, T2 documents, T3 `prompts.csv`, T4 `ai_tools.csv`, then T5, R1 text, R2 video, R3 slides.
**Problems / decisions needed:**
- `data/org/org.yaml` and `data/ai_tools.csv` are still templates, so the seed uses `data/org/org.sample.yaml` and `data/ai_tools.sample.csv` (invented). It switches by itself when the real files have more than 2 teams, no "TBD" in the company name and 5 or more tools. They should copy the sample's shape (storyline `kind` is one of tool_spike, api_key_paste, contract_paste, salary_questions, memo_rebuild; tool domains in the CSV are separated by `;`).
- The PRD names a `seed` compose service; seeding runs inside the brain start instead, because a one-shot container can break `docker compose up --wait` on some versions. Re-seed with `make reset` then `make up`.
- After every pull that touches `infra/db`, compose or a Dockerfile: `make reset` then `make up` (rule is in CLAUDE.md). A stale gateway image makes the live gateway tests fail until `make up --build` runs again.
- No login yet: `PUT /v1/policies`, `POST /v1/keys` (off when `DEMO_MODE=false`) and the dashboard APIs are open to anyone who can reach the ports.
- `OPENAI_API_KEY` empty means the chat answers with the offline `demo-mock` model (same text for every message). Set it in `.env` for real answers.
- Warn card has Edit message / Send anyway / Cancel (PRD wanted "Send without it"; the brain returns no masked text for warn). Chat has no file attach and no history sidebar. Streamed answers arrive as one text chunk (kept whole so secrets split across chunks are caught).
- `.env.example` should list `LITELLM_MASTER_KEY=sk-admin-change-me` (the tools could not edit that file; compose has the same default).
- Still missing from the PRD overview: the weekly question box (A1) and a team filter on incidents.
**Files touched:** services/brain/src/brain/{seed/*,db/tables.py,queries.py,records.py,main.py,config.py,api/schemas.py,policy/store.py}, services/brain/tests/{test_seed.py,test_dashboard_api.py}, web/src/{pages/security/*,components/*,lib/*,test/fixtures.ts,App.tsx}, web/e2e/smoke.spec.ts, data/org/org.sample.yaml, data/ai_tools.sample.csv, scripts/gen_org.py, docker-compose.yml, TASKS.md, PROGRESS.md

---

## 2026-11-14 00:00, Alexandros, task G2 (streaming)
**Done:** Streaming answers (`stream: true`) are now filtered and unmasked like normal ones. The gateway collects the whole streamed answer first (a secret or a placeholder such as `[IBAN_1]` can be split across chunks, and a half-seen value cannot be filtered), cleans it through `/v1/inspect-output` and `/v1/unmask`, and sends it in the first text chunk; role, finish and usage chunks pass through in order. If the brain is down nothing is shown (503). G2 is complete.
**State:** branch `task/G2-streaming`, PR open. `make check` green (63 brain tests); `make test-gateway` 8 live tests green (2 are streaming).
**Next step:** W6 (axe + 390 px on every route, so far only `/chat` is real) or W2 (Security overview + inventory + incidents list, needs O1/O2 data from Stelios). Ask which first.
**Problems / decisions needed:** The stream arrives as one text chunk, so the typing effect is lost for streamed answers. A chunk-by-chunk version (hold back text after an unclosed `[`, filter per sentence) is possible later if the demo needs it. The chat page does not stream yet. The `x-dna-decision` header is not set on streamed responses.
**Files touched:** infra/gateway/{dna_inspect.py,dna_guardrail.py}, services/brain/tests/{test_gateway_logic.py,test_gateway_live.py}, TASKS.md, PROGRESS.md

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
