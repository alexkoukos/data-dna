# PIVOT: from AI gateway to browser extension

Status: approved by Alex on 17 Nov 2026 with all recommendations accepted. Done on branch `task/pivot-extension`; see "What was done" at the end.
Branch: `task/pivot-extension`. Date: Tue 17 Nov 2026.

## What changes

Today the demo path is: employee uses Company Chat (web) or an API key, the LiteLLM gateway calls the brain, the brain decides. The new demo path is: a Chrome extension (MV3) on chatgpt.com, claude.ai, gemini and a local `mock-ai` page, which checks text where the employee pastes it, and talks to the same brain. The web app becomes the admin dashboard only.

The product name stays **Sentry** (the pivot brief had a `{{NAME}}` placeholder; the repo, brand pack and README already use Sentry). "Data DNA" only names the leak-attribution feature.

## Keep and reuse (no rewrite)

| Area | Where | Use in the pivot |
|---|---|---|
| Detection engine: validators, normalisation, patterns, Greeklish, confusables, YARA, entities, layers | `services/brain/src/brain/detection/` | Becomes L2 behind `/v1/check`. Patterns and validators are also ported to TypeScript for L1 (see "Decisions"). |
| Documents: chunking, MinHash, embeddings, registry, session memory | `services/brain/src/brain/documents/`, `sessions.py` | L2 copy, paraphrase and rebuild-across-prompts checks. |
| Policy engine, groups, store, `policies.yaml` | `services/brain/src/brain/policy/` | Policy editor and the extension policy cache (add ETag and version). |
| Injection checks | `services/brain/src/brain/injection/` | Bonus check on pasted text. |
| Incidents, reveal, sealed identity, audit log | `records.py`, `reveal.py`, `/v1/incidents*`, `/v1/reveal-requests*` | Dashboard incidents and the two-person reveal. |
| Inventory and shadow AI | `shadow/`, `/v1/inventory`, `data/ai_tools.csv` | Merge extension telemetry with Squid and Zeek logs. |
| Analyst questions with SQL shown | `ask/`, `queries.py`, `/v1/ask*` | Dashboard "Ask" page, unchanged. |
| Seeding and generator | `seed/`, `scripts/gen_org.py`, `data/org/org.yaml` | Emit extension telemetry events instead of gateway calls. |
| Eval harness and data | `eval/`, `brain/eval/run.py`, `data/eval/`, `make eval` | Extend with L1 vs L2 and latency. |
| Impact, history, groups, weekly, coaching, DNA marks, honeytokens | brain modules and web pages | Dashboard pages, kept. |
| Ollama (profile `local`) | `docker-compose.yml` | Backs `/v1/ask-local` for the redirect outcome. |
| CI, Makefile, devcontainer, brand pack, mascot | `.github/`, `Makefile`, `docs/brand/` | Kept. CI gets extension lint, tests and e2e jobs. |

## Park (stays in the repo, out of the demo path)

- **LiteLLM gateway**: `infra/gateway/`, the `gateway` compose service, `/v1/keys`, `/v1/inspect-output`, `/v1/unmask`, the Anthropic-format endpoint, MCP proxy (`scripts/mcp_proxy.py`), `tools/paste_guard.py`, `docs/GATEWAY_SETUP.md`, `make test-gateway`. README gets a short "Other ways in" section. No new work on it.
- **Connect page** (`ConnectPage.tsx`): keep the route for the gateway story, but the extension download page replaces it in the nav.
- **Break-it page** (`BreakItPage.tsx`, `/v1/try*`): keep as a public "try the detector" page; it does not need the extension.
- **Simulator** (`scripts/simulate.py`): keep, and change its output to extension events.

## Delete (only after your OK)

- `web/src/pages/ChatPage.tsx` and its test, `components/{Composer,MessageBubble,StarterPrompts,ChatSkeleton}.tsx`, `lib/chatApi.ts`: the Company Chat. `WarnCard`, `WhyPanel`, `OutcomeChip`, `NextStep` are reused by the dashboard (incident detail) and as the model for the extension overlay, so they stay.
- The onboarding and home flow that sends people into the chat (`HomePage.tsx`, `NextStep.tsx` links into chat). Rewrite Home as a short "Get the extension" start page instead of deleting it outright.
- The chat steps in `web/e2e/` and the compose smoke test. Replaced by Playwright with the extension loaded.

Nothing in the brain is deleted.

## New

- `extension/` (WXT, TypeScript strict, React for popup, options, side panel). Adapters hold all DOM selectors. Start with mock-ai, then chatgpt.com, claude.ai, gemini.
- `mock-ai/` (static ChatGPT-like page for offline demo and e2e).
- `shared/rules.json`, `shared/ai-tools.json`, `shared/fixtures/` loaded by both the Python and TypeScript test suites.
- Brain: `POST /v1/check` (L1 result in, final action out, wraps the current `/v1/inspect` pipeline), `POST /v1/events` (telemetry, no text), `GET /v1/policy` (ETag), `POST /v1/ask-local`, `POST /v1/logs/ingest`, device pairing (6-digit code, bearer token). New numbered DB file in `infra/db/` for devices and telemetry (run `make reset` after pulling).
- `web` serves `/extension.zip` (multi-stage build in `web/Dockerfile`).
- `deploy/chrome-policy.json` example.

## Decisions I need from you

1. **Directory names.** The brief's target layout says `brain/` and `dashboard/`. The repo has `services/brain/` and `web/`, and CI, Makefile, compose, CLAUDE.md and PROGRESS entries all point there. I recommend keeping `services/brain/` and `web/` and adding only `extension/`, `mock-ai/`, `shared/`, `deploy/`. Renaming a day before freeze risks breaking CI for no judge-visible gain.
2. **Rules shared as JSON.** The brain has rules in Python (`detection/patterns.py`, `rules/`, `validators.py`). I propose extracting the L1 subset (checksummed IDs, cards, IBAN, emails, phones, keys) into `shared/rules.json` with shared fixtures, and having the Python side load it. Checksums stay as named functions in each language, tested on the same fixtures. Greeklish, confusables, YARA and entities stay Python-only (L2).
3. **Compose.** The brief wants no `gateway` in the demo path. I would move `gateway` behind a compose profile (`gateway`), like `ollama` and `sim` already are. This changes the compose topology, so I am asking first.
4. **Delete list above**, especially Home and the chat e2e tests.
5. **Branching.** CLAUDE.md says one branch per task and a PR into `main`. I will use `task/pivot-extension` for PIVOT and the scaffold, then one branch per later step.
6. **Open work on other branches.** `task/X-remaining` is noted as uncommitted in PROGRESS but `main` already has the X work merged. `S2` and `T5` are still open on the board. They do not conflict with the pivot, but the pivot replaces R1 (README) content, so I would write the README after the extension runs.

## Order of work after your OK

1. Scaffold `extension/`, `mock-ai/`, `shared/rules.json`; mock-ai mask and unmask loop with Vitest and one Playwright test.
2. Add the extension zip to the web image so `docker compose up --build` serves `/extension.zip`.
3. `/v1/check`, policy ETag, events, pairing. Then adapters, overlay cards, inventory from telemetry and logs, dashboard changes.

## What was done (17 Nov 2026)

- Deleted: Company Chat page, its components, its tests and its e2e steps. Home is now a short "Get the extension" start page.
- Kept the brain, detection, documents, policy, incidents, reveal, inventory and analyst code. Added `brain/extension.py` (`/v1/check`, `/v1/events`, `/v1/policy` with ETag, `/v1/pair`, `/v1/ask-local`, `/v1/logs/ingest`, `/v1/demo-users`), two tables (`devices`, `ext_events`, file `infra/db/06-extension.sql`) and CORS.
- Added `extension/` (WXT, TypeScript strict), `mock-ai/`, `shared/rules.json` with `shared/fixtures/l1.json` (tested by both the brain and the extension), `samples/`, `deploy/`.
- Decisions as proposed: directory names kept (`services/brain`, `web`); L1 subset in `shared/rules.json` while Greeklish, confusables, YARA and entities stay in Python; the gateway is behind the compose profile `gateway` (`make gateway`); web build context is the repository root so the web image also builds `/extension.zip`.
- Parked: gateway, `/v1/keys`, MCP proxy, paste guard, Connect page, Break-it page.
- Seed: browser tools now produce extension incidents and visit events on every team except Operations, so the logs-only story (unapproved DeepSeek in Operations) shows in the inventory.
- Not done: fail mode per category in the policy editor, Firefox build, a measurement of the compose stack on Linux (no Docker in the session that built this).
