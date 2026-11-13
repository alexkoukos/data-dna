# PRD: Data DNA, the AI gateway that keeps company data inside

Netcompany Hackathon Athens 2026, Challenge 3: Shadow AI protection and Data Protection.
Team: Alexandros (gateway, web app, Docker, CI), Stelios (detection, routing, DNA, MCP, eval, synthetic org), Vasilis (research, business, policy), Konstantinos (data, story, video, slides, pitch).
Submission: Friday 20 Nov 2026, judged from the GitHub repo alone. Pitch for finalists: 26 Nov.

This document is the build spec. Read it fully before writing code. When something here conflicts with a later decision in an issue or commit, the later decision wins; update this file.

---

## 1. One sentence

Data DNA is an AI gateway that every AI tool in the company goes through: it discovers which AI tools are used (including hidden ones, from network logs), catches sensitive data before it leaves (even when rewritten), and decides per prompt: allow, warn, mask, answer with a local model, or block.

## 2. Hard rules from Netcompany (failing any of these voids or hurts the submission)

| Rule | Source | How we comply |
| --- | --- | --- |
| `git clone` + `docker compose up --build` on Linux must build and start everything | slide 6, 8 | Single compose file, health checks, seeded data, CI smoke test on every push |
| Only official vendor images for databases | slide 6 | `postgres:16` official image; pgvector installed in our own Dockerfile `FROM postgres:16` |
| External data only from official public APIs or our own mock data | slide 6 | OpenAI API, Hugging Face model downloads, Ollama model pull; all business data synthetic |
| No real personal data of other people | slide 6 | Faker-generated people, fictional companies |
| README: concept, main features, setup and run, architecture | slide 6, 8 | README outline in section 18 |
| Secure management of API keys | slide 8 | `.env` (gitignored) + `.env.example`; real keys only inside the gateway; gitleaks in CI |
| Cross-platform | slide 8, 10 | Multi-arch images (amd64, arm64); tested on Linux, macOS Apple silicon, Windows WSL |
| Starts without our help | implied | Works with no OpenAI key (local model fallback); seeded dashboard on first start |

## 3. Scoring and what each criterion needs from the code

| Area (weight) | Criterion | What the code must show |
| --- | --- | --- |
| Innovation 25% | Novelty, creativity | Paraphrase detection, cross-prompt rebuild tracking, local-model routing, per-copy attribution, MCP inspection |
| Business 15% | Market, applicability, future usage | Realistic scenario data; roadmap in README (written by DET) |
| Technical 25% | Working state | Every P0 feature works from a clean clone |
| Technical 25% | Code quality | Typed code, linters, tests, coverage report, clear module boundaries |
| Technical 25% | Optimization and efficiency | Cheapest check first, caching, measured latency and zero-LLM-token share |
| Technical 25% | Modern tools | LLM gateway, embeddings, local LLM, MCP, injection classifier |
| Technical 25% | Cross-platform | Multi-arch build, platform test matrix |
| UX 15% | Intuitive, no training | Every outcome explains itself in one line; onboarding in 30 seconds |
| UX 15% | Cross-device | Responsive React app, usable at 390 px width |
| UX 15% | Accessibility | WCAG AA contrast, keyboard navigation, labels, axe checks pass |
| UX 15% | Engagement and stickiness | Company Chat is pleasant enough that people prefer it: history, templates, fast answers |
| Pitch +20% | Finalists only | Demo mode with scripted replay |

## 4. Netcompany's six guiding questions, answered by the design

| Question (slide 21) | Our answer |
| --- | --- |
| 1. Where do you look? | An AI gateway in front of all LLM calls (chat, API, agents, MCP), plus proxy and DNS logs for traffic that bypasses it. Browser extension is roadmap. |
| 2. What counts as sensitive? | PII (names, emails, phones), credentials (API keys, passwords, tokens), source code, client names, Greek IDs (AFM, AMKA) and IBAN validated by checksum, and text from registered confidential documents, even paraphrased. |
| 3. Rules, ML or LLM? | All three, cheapest first: regex and Presidio (~1 ms), MinHash and embeddings (~10 ms), LLM judge only for borderline scores, cached. We report cost and latency per prompt. |
| 4. What happens on a hit? | Five outcomes: allow, warn and educate (with a reason box), mask and forward (unmask in the answer), answer with the local model, block. Every outcome suggests the approved path. |
| 5. How do you prove it works? | Labelled synthetic test set, precision and recall per leak type versus a regex baseline, red team with promptfoo and garak, injection prompts, fixed targets. |
| 6. Who watches the watcher? | Drop-by-default, fingerprints not text, sealed identity with two-person reveal and audit log, 30-day retention, GDPR Art. 5 and 25, EU AI Act transparency. |

### Netcompany's Tech Toolbox (slide 22), mapped to our choices

| Toolbox card | Suggested there | We use |
| --- | --- | --- |
| LLM providers | OpenAI (keys provided); Llama, Mistral, Qwen via Ollama | OpenAI for clean and masked prompts; Qwen via Ollama for confidential content |
| Detection and DLP | Presidio, spaCy NER, regex and YARA rules, LLM classifiers with Pydantic | All of them: regex with checksums, Presidio + spaCy (en, el), YARA rules for secrets and source code, LLM judge with Pydantic output |
| Interception and gateways | LiteLLM proxy, mitmproxy, browser extensions, Squid or Zeek logs | LiteLLM gateway + Squid and Zeek logs (synthetic); extension on the roadmap |
| Data and frontend | PostgreSQL, OpenSearch; Streamlit, React or Grafana; chat assistant for SOC analysts | PostgreSQL + pgvector, React, analyst question box |
| Guardrails and injection | NeMo Guardrails, Guardrails AI, Llama Guard, Prompt Guard, input and output filtering | Injection classifier (Prompt Guard family when a token is available), input AND output filtering |
| Evaluation and red teaming | Labelled sets, precision and recall, promptfoo or garak, LLM-as-judge | All of them, in `make eval` |

## 5. Users

| Persona | Goal | Surface |
| --- | --- | --- |
| Employee (non-technical) | Use AI for daily work without worrying what is allowed | Company Chat |
| Developer / agent builder | Point any tool or SDK at a safe endpoint | Onboarding page, API, MCP |
| Security analyst | See AI use, incidents, risk; answer questions fast | Security dashboard |
| DPO / second approver | Approve or deny identity reveals | Reveal request screen |
| Document owner | Register confidential documents, approve DNA marks | Documents page |

## 6. Scope

**P0, must work on 20 Nov (never cut)**
- One-command start, seeded database, health checks
- Gateway with per-user virtual keys (LiteLLM), OpenAI-compatible endpoint
- Normalisation, pattern checks (incl. Greek IDs, client names, source code), document checks (MinHash + embeddings)
- Policy engine with allow, warn, mask, block; unmask in answers
- Company Chat with all outcomes visible and explained, file upload (PDF, DOCX)
- Shadow AI: Squid and Zeek log ingestion, AI tool inventory with risk ratings
- Security dashboard: overview, inventory, incidents, policy editor
- `make eval` with targets, results in README
- CI: lint, types, unit, integration, compose smoke test
- README in the required parts

**P1, should have**
- Local-model routing (Ollama)
- Session memory: rebuild across prompts, puzzle view
- DNA: marked copies and copy attribution with confidence, sealed identity and reveal flow
- Analyst questions in plain language (5 presets + free text), showing the SQL
- Onboarding page with copyable snippets
- Prompt-injection checks on tool results and documents
- Playwright end to end + axe
- Demo mode (scripted replay)

**P2, cut first (in this order)**
1. MCP gateway
2. Anthropic-format endpoint (Claude Code demo)
3. LLM judge for borderline cases
4. Free-text analyst questions (keep presets)
5. PDF export of marked copies

**Non-goals:** real browser extension, TLS interception, real company data, SSO, multi-tenant SaaS.

## 7. Architecture

```
                     +-------------------+
 Employee  --------> |  web (React/Vite) |----+
                     +-------------------+    |
 SDKs / agents / Claude Code -------------+   |
                                          v   v
                                   +----------------+     pre_call / post_call hooks
                                   | gateway        | <----------------------------+
                                   | (LiteLLM)      |                              |
                                   +----------------+                              |
                                     |      |      \                               |
                         cloud LLM <-+      |       +-> local LLM (ollama)         |
                         (OpenAI)           |                                      |
                                            v                                      |
                                   +----------------+   checks, policy, scoring    |
 MCP clients ---> mcp-proxy -----> | brain (FastAPI)|------------------------------+
                                   +----------------+
                                            |
                 log-ingest (Squid/Zeek) -> |  postgres (+pgvector)
                                            v
                                   +----------------+
                                   | db             |
                                   +----------------+
```

**Compose services**

| Service | Image / build | Port | Notes |
| --- | --- | --- | --- |
| `db` | build `infra/db` (FROM `postgres:16` + pgvector) | 5432 (internal) | Init SQL + seed |
| `brain` | build `services/brain` (Python 3.12) | 8001 | Detection, policy, DNA, dashboard API, analyst SQL |
| `gateway` | `ghcr.io/berriai/litellm` (pinned tag) | 4000 | Virtual keys, routing, custom guardrail calling `brain` |
| `ollama` | `ollama/ollama` (pinned tag) | 11434 (internal) | Pull model on start via entrypoint; P1 |
| `web` | build `web` (Node build, served by nginx official image) | 3000 | React app |
| `mcp-proxy` | build `services/mcp_proxy` | 8002 | P2 |
| `seed` | same image as `brain`, one-shot | none | Generates synthetic logs, docs, users, incidents if DB empty |

Every service has a health check; `web` depends on `brain` and `gateway` being healthy. Model downloads happen at first start (embeddings from Hugging Face cached in a named volume; Ollama model pulled into a volume). Nothing large is committed.

**Environment (`.env.example`)**
```
OPENAI_API_KEY=            # optional; without it clean prompts go to the local model
LITELLM_MASTER_KEY=sk-admin-change-me
DB_PASSWORD=change-me
OLLAMA_MODEL=qwen2.5:3b
EMBED_MODEL=intfloat/multilingual-e5-small
RETENTION_DAYS=30
DEMO_MODE=true
```

## 8. Request flow

1. Client calls `gateway` with a personal key (`sk-u-...`). LiteLLM resolves key to user and team.
2. LiteLLM `pre_call` guardrail sends `{user_id, team, model, messages, attachments}` to `brain POST /v1/inspect`.
3. `brain` runs the pipeline (section 9) and returns `{decision, reasons[], masked_messages?, route?, incident_id?}`.
4. Gateway acts:
   - `allow`: forward to requested cloud model.
   - `mask`: forward `masked_messages`; `post_call` hook calls `brain POST /v1/unmask` to restore values in the answer for this user only.
   - `local`: forward to `ollama` model instead.
   - `warn`: return HTTP 409 with a structured body `{type:"warn", message, reasons, options}`; Company Chat shows the warn card; the client retries with header `X-DNA-Ack: <reason text>` to proceed.
   - `block`: return HTTP 403 with `{type:"block", message, reasons, approved_alternative}`.
5. Output filtering: the LiteLLM `post_call` hook sends every model answer to `brain POST /v1/inspect-output`, which runs the pattern checks and injection checks on the response (a model can echo secrets or carry injected instructions from tools). Hits are masked in the answer and logged.
6. Every non-allow decision writes an incident (masked, no raw prompt). Allow decisions write only a counter row.

Streaming must work for allow, mask (unmask streamed chunk-wise via a placeholder map) and local.

## 9. Detection pipeline (brain)

Order matters: cheapest first, stop early on a decisive block.

### 9.1 Normalisation
- Extract text from attachments: PDF (pypdf or PyMuPDF), DOCX (python-docx).
- Unicode NFKC, strip zero-width and bidi control characters.
- Collapse digits separated by spaces, dots or dashes into a candidate stream for ID checks (keep original offsets).
- Detect and decode base64 / hex blobs over 16 chars; inspect decoded text too.
- Record `evasion_signals[]` (base64 found, zero-width found, spaced digits) as their own reasons.

### 9.2 Pattern checks
| Entity | Rule |
| --- | --- |
| AFM | 9 digits; check digit = (sum of d[i] * 2^(8-i) for i in 0..7) mod 11 mod 10 equals d[8]; reject all-zero |
| AMKA | 11 digits; first 6 are a valid DDMMYY date; whole number passes Luhn |
| IBAN | Country + 2 check digits + BBAN; mod-97 of rearranged string equals 1; GR length 27 |
| Card | 13 to 19 digits, Luhn |
| API keys / secrets | Known prefixes (`sk-`, `sk-live-`, `AKIA`, `ghp_`, `xoxb-`, `AIza`), high-entropy tokens near words like key, token, secret, password |
| Email, phone, person names | Presidio analyzer (en + el via spaCy models; fall back to regex for Greek phones `+30` / `69xxxxxxxx`) |
| YARA rules | `rules/*.yar` for private keys (PEM blocks), cloud credentials, connection strings, internal hostnames and code markers (license headers, package names of company repos); run with yara-python |
| Client names | Case-insensitive, accent-insensitive match against `clients` table (aho-corasick) |
| Source code | Heuristic classifier (keyword density, brackets, indentation) + MinHash match against fingerprints of the company's registered repos |

Each finding: `{entity, start, end, confidence, masked_preview}`. Never store raw values.

### 9.3 Document checks
- Registration: split document into chunks of ~60 words with 50% overlap. Store per chunk: MinHash signature (datasketch, 128 perms, 5-word shingles), embedding (multilingual-e5-small, normalised), chunk index, document id. Store no text in production mode (demo mode may store text for the puzzle view only, flagged).
- Query: chunk the prompt the same way. MinHash LSH lookup (Jaccard >= 0.5 = near-copy). Embedding cosine via pgvector (threshold tuned on eval set; start at 0.82). Score per document = max chunk score; also count matched chunk indices.
- Return `{document_id, sensitivity, matched_chunks[], score, kind: copy|paraphrase}`.

### 9.4 Session memory (P1)
- Key: `(user_id, document_id)`, window 24 h, stored in Postgres.
- Track union of matched chunk indices. Coverage = matched / total chunks.
- Rule: coverage over policy threshold (default 40%) or 3+ prompts hitting one restricted document escalates to block. Show "60% of Board_Memo rebuilt from 3 prompts".

### 9.5 Prompt injection (P1)
- Applies to tool results (MCP), uploaded documents and retrieved content flowing into an agent.
- Classifier: `protectai/deberta-v3-base-prompt-injection-v2` (open download). Optional: Llama Prompt Guard 2 if an HF token is provided (gated model). Chunk to 512 tokens.
- Plus heuristics: "ignore previous instructions" family in en and el.

### 9.6 LLM judge (P2)
- Only when document score is within a band around the threshold (e.g. 0.75 to 0.85).
- Prompt asks for structured JSON `{is_confidential_content: bool, reason}` (Pydantic). Cache by SHA-256 of normalised text. Count tokens.

## 10. Policy engine

Config in DB, editable in the dashboard, seeded from `policies.yaml`:

```yaml
defaults:
  on_gateway_down: { restricted: fail_closed, other: fail_open }
categories:
  greek_id:     mask
  iban:         mask
  card:         mask
  secret:       mask
  person_email_phone: mask
  client_name:  warn
  source_code:  warn
  injection:    block
documents:
  sensitivity:
    internal:     local
    confidential: local
    restricted:   block      # crown-jewel
session:
  rebuild_coverage_block: 0.4
  max_prompts_per_restricted_doc: 3
```
Precedence: block > local > warn > mask > allow. Every decision returns human-readable `reasons[]` and an `approved_alternative` string.

## 11. Shadow AI discovery

- Inputs: Squid `access.log` (native format) and Zeek `dns.log` (TSV), synthetic, generated by `seed` for ~200 users over 14 days, mounted at `/data/logs`.
- `ai_tools` catalog: name, vendor, domains[], category, approval (approved, tolerated, unapproved), risk (low, medium, high), reason, approved alternative. Seeded from DET's spreadsheet (`data/ai_tools.csv`).
- Ingest job matches domains, aggregates per tool, team, user (pseudonymised), day.
- Gateway traffic counts as the approved "Company AI" tool.
- Inventory view: tool, approval, risk, teams, users, requests, 7-day trend, first seen.

## 12. DNA: per-copy attribution (P1)

- Owner marks a document as `restricted` and asks for DNA.
- LLM proposes 6 to 8 insertion points and, for each, 4 variants of an added decoy detail (project codename, internal reference number, illustrative example name). Hard rule in prompt and validation: never change dates, amounts, names of real parties, legal terms. Owner approves in UI.
- Each recipient gets a copy id; variant per mark chosen so any two copies differ in at least half the marks (code with good minimum distance).
- Detection: when a document match occurs on a DNA document, search matched text for any variant of each mark (fuzzy, accent-insensitive). Score each copy by matching marks.
- Confidence: with k marks found and all matching one copy, P(coincidence) = (1/4)^k. Show "5 marks found, all 5 match copy 7F3A, 1 in 1,024 chance of coincidence". If marks conflict, show the top 2 copies (collusion case).
- Recipient identity is a pseudonym. Reveal: request with reason by analyst, approval by DPO role, then identity shown; every step written to `audit_log` (append-only table, no update/delete grants).
- Copies rendered as HTML pages (P1), PDF via WeasyPrint (P2).

## 13. Analyst questions (P1)

- Five preset questions as parameterised SQL (fast, always works), including: "Which teams sent client data to unapproved AI tools this week?"
- Free text (P2): LLM converts to SQL against a read-only DB role that can only see views `v_incidents`, `v_tool_usage`, `v_inventory`; reject anything not `SELECT`; limit 500 rows; show the SQL beside the answer.

## 14. Data model (Postgres)

```
users(id, pseudonym, team, role, created_at)              -- real names only in seed demo
api_keys(id, user_id, key_hash, created_at, revoked_at)
clients(id, name, aliases[])
documents(id, title, owner_id, sensitivity, dna_enabled, created_at)
doc_chunks(id, document_id, idx, minhash bytea, embedding vector(384), text_demo nullable)
doc_marks(id, document_id, position, variants text[])
doc_copies(id, document_id, copy_code, recipient_user_id, variant_vector int[])
incidents(id, ts, user_id, team, tool, channel, decision, categories[], document_id, copy_code,
          score, reasons jsonb, masked_preview, expires_at)
session_coverage(user_id, document_id, chunk_idx int[], prompts int, window_start)
ai_tools(id, name, vendor, domains[], category, approval, risk, reason, alternative)
tool_usage_daily(day, tool_id, team, users, requests)
policies(id, scope, key, action, updated_by, updated_at)
reveal_requests(id, incident_id, requested_by, reason, approved_by, status, ts)
audit_log(id, ts, actor, action, target, details jsonb)     -- append-only
counters_daily(day, team, allowed, checked, zero_llm, llm_tokens)
```
Retention job deletes incidents past `expires_at` daily.

## 15. Brain API (FastAPI, OpenAPI docs at /docs)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | /v1/inspect | Run pipeline, return decision |
| POST | /v1/inspect-output | Output filtering on model answers |
| POST | /v1/unmask | Restore masked values in a response for a session |
| POST | /v1/documents | Register document (multipart) |
| POST | /v1/documents/{id}/dna/propose | LLM proposes marks |
| POST | /v1/documents/{id}/dna/approve | Owner approves marks |
| POST | /v1/documents/{id}/copies | Issue copies for recipients |
| GET | /v1/incidents | List with filters |
| GET | /v1/incidents/{id} | Detail, puzzle data, copy attribution |
| POST | /v1/reveal-requests, /{id}/approve | Sealed identity flow |
| GET | /v1/inventory | AI tools with usage |
| GET/PUT | /v1/policies | Policy editor |
| POST | /v1/ask | Analyst question |
| POST | /v1/keys | Create personal key (onboarding) |
| GET | /v1/metrics | Latency, zero-token share, counts |
| GET | /healthz | Health |

## 16. Web app (React + Vite + TypeScript strict + Tailwind)

Apply `frontend-design-principles` (Refactoring UI, Baranov typography, Nielsen's 10 heuristics, Better Stories copy). Token scales for spacing, type, color, shadows, radii defined once in Tailwind config. Presentational vs container components. Skeleton loaders, empty states, friendly errors.

| Route | Screen | Key content |
| --- | --- | --- |
| `/chat` | Company Chat | Messages with outcome chips (icon + text, never color alone): Allowed, Masked, Answered locally, Warned, Blocked; "Why?" disclosure; warn card with reason input and three actions (Send without it / Send anyway / Cancel); attach file; history sidebar; templates |
| `/connect` | Onboarding | Endpoint URL and personal key with copy buttons; tabs: OpenAI SDK (Python, JS), Claude Code (`ANTHROPIC_BASE_URL`), n8n, MCP; "Waiting for first request" live status |
| `/security` | Overview | KPI row (prompts checked, zero-LLM share, incidents, unapproved tools), weekly question box, recent incidents |
| `/security/tools` | Inventory | Table with approval, risk, teams, users, trend; filter; alternative |
| `/security/incidents` and `/:id` | Incidents | List; detail with puzzle view (leaked chunks highlighted and numbered, % rebuilt), timeline of prompts, copy attribution card with confidence, sealed identity and "Request reveal" |
| `/security/documents` | Documents | Register, sensitivity, DNA marks approval, issued copies |
| `/security/policies` | Policies | Action per category and sensitivity; preview of effect |
| `/security/ask` | Ask | Presets + free text; answer table + SQL shown |

Requirements: responsive down to 390 px (sidebar stacks), touch targets 44 px, WCAG AA contrast, keyboard focus visible, `aria-label` on icon buttons, UI language English with Greek content support (Inter font, Greek glyphs). Demo data badge on dashboard.

## 17. Non-functional targets (checked by `make eval` and load test)

| Metric | Target |
| --- | --- |
| Recall, fully paraphrased document leaks | >= 80% |
| False alarms on clean prompts (incl. same-topic) | <= 5% |
| Added latency p95, without LLM judge | < 100 ms |
| Prompts handled with zero LLM tokens | >= 90% |
| Correct copy named, leaks with >= 3 marks | >= 90% |
| Cold start to healthy (after images pulled) | documented; models cached in volumes |
| RAM for full stack | measured and stated in README (expected about 8 GB) |

## 18. Evaluation harness

- `data/eval/prompts.csv` columns: `id, lang (el|en), text, label (leak|clean|injection|evasion), leak_type (copy|edit|paraphrase|split|pattern), document_id, entity_types, expected_decision, notes`. Written and labelled by DET, ~200 rows; plus LLM-generated paraphrases via `scripts/gen_paraphrases.py` (output committed).
- Baseline: regex + keyword list only.
- `make eval` prints and writes `eval/report.md` and `eval/report.json`: precision, recall, F1 per leak type and language, false alarm rate, injection catch rate, copy attribution accuracy, latency p50/p95, zero-LLM share, tokens used. Pass/fail against section 17 targets.
- Red team: `promptfoo` config in `eval/promptfoo/`, `garak` run script; results summarised in the report.

## 19. Testing and CI

| Level | Tools | Must cover |
| --- | --- | --- |
| Lint, types | ruff, mypy (strict on brain), ESLint, Prettier, tsc | Whole repo |
| Unit | pytest | AFM/AMKA/IBAN/Luhn validators (valid and invalid fixtures), normalisation, MinHash and embedding matchers (with tiny model or mocked), session scoring, policy precedence, DNA code distance and attribution math |
| Integration | pytest + compose | Each of the five outcomes through the gateway with a mocked LLM; streaming; unmask; key to team mapping |
| API compatibility | openai and anthropic Python SDKs as clients | Requests succeed unchanged against the gateway |
| Frontend | Vitest + Testing Library | Outcome chips, warn card actions, copy buttons |
| End to end | Playwright | Paste confidential paragraph -> "Answered locally"; warn flow; analyst weekly question |
| Accessibility | @axe-core/playwright | No serious violations on every route |
| Performance | Locust or k6 | p95 latency target |
| Security | gitleaks, pip-audit, npm audit, Trivy | No secrets, no critical vulns |
| Smoke | GitHub Actions | `docker compose up --build`, wait healthy, one request per outcome |
| Platforms | Docker Buildx | Build amd64 and arm64 |

Coverage target: 80% on `services/brain`. Manual: clean clone on a second machine every evening; Thursday 19 Nov full run on Linux, macOS Apple silicon, Windows WSL.

## 20. Repo layout

```
/README.md
/docker-compose.yml
/.env.example
/Makefile                 # up, down, seed, eval, test, lint
/infra/db/                # Dockerfile (postgres + pgvector), init.sql
/infra/gateway/           # litellm config.yaml, custom guardrail module
/services/brain/          # FastAPI app: api/, detection/, policy/, dna/, shadow/, ask/, db/
/services/mcp_proxy/
/web/                     # React app
/data/                    # seed inputs: ai_tools.csv, clients.csv, documents/, eval/
/scripts/                 # gen_logs.py, gen_paraphrases.py, demo_replay.py
/eval/                    # harness, promptfoo, garak, reports
/docs/                    # architecture.png, decisions.md
/.github/workflows/ci.yml
```

## 21. Demo mode and video support

- `DEMO_MODE=true` seeds the synthetic organisation from section 21a: 200 users, 8 teams, 10 clients, 3 confidential documents (one restricted with DNA and 12 copies), 14 days of logs with the storyline, and the incidents it produces.
- `scripts/demo_replay.py` replays the scripted demo prompts in order (works without internet if OpenAI key missing: local model answers).
- Every screen in the demo path must look good at 1920x1080 for recording and at 390 px for the cross-device shot.

**Demo script (video and live)**
1. Inventory: "12 AI tools in use this week, 4 unapproved, found in the logs".
2. Onboarding: copy URL and key into a tool, first request turns status green.
3. Prompt with IBAN and API key: masked, answered, values restored on screen only.
4. Paraphrased paragraph of the board memo: caught, answered locally, badge. Regex baseline misses it.
5. Two more pieces: "60% rebuilt from 3 prompts, blocked".
6. Copy named with confidence; identity sealed; reveal needs DPO.
7. Analyst asks the weekly question, answer + SQL.
8. Evaluation table.

## 21a. Synthetic organisation and employee simulator

The whole demo lives inside one fictional company. Netcompany allows only synthetic data; we make that a strength.

- **Spec input (from Konstantinos and Vasilis):** `data/org/org.yaml` with company name, teams (8, with size and roles), clients (10), AI usage profile per team (which tools, how often, through gateway or not), and the 14-day storyline (named events on given days).
- **Generator:** `scripts/gen_org.py --seed 42` produces users (Faker `el_GR` names), reporting lines, personal API keys, clients, documents registration, Squid and Zeek logs, gateway traffic history and the resulting incidents. Fully deterministic: same seed, same company for every judge. Runs in the `seed` service when the DB is empty.
- **Storyline events** (examples, final list from DET): one employee rebuilds the board memo across days; one team's use of an unapproved tool spikes; a developer pastes an API key; a legal team member pastes a client contract; HR asks about salaries.
- **Employee simulator (P1):** `scripts/simulate.py` (also a compose profile `sim`) sends real requests through the gateway with different users' keys, drawn from `data/eval/prompts.csv` and the storyline, at a configurable rate. During the demo the dashboard updates live. Uses the local model or a stub response by default, so it costs no OpenAI tokens.
- **No model training anywhere.** The local LLM (Ollama) and the embedding and injection models are used pretrained. Only thresholds are calibrated on the labelled set. Registering a new document protects it in seconds. Fine-tuning a small Greek classifier is roadmap, not scope.

## 21b. Local LLM: the likely bottleneck (to be measured, decision on Sat 14)

Docker on macOS has no GPU access, so the local model runs on CPU on a judge's laptop: few tokens per second, slow first load, queueing under concurrent requests. Detection itself is not the bottleneck (milliseconds).

Mitigations, all P1:
- Route only confidential prompts to the local model; everything else goes to OpenAI.
- Smallest model with acceptable Greek: benchmark 1B to 4B candidates (e.g. Gemma 3, Qwen 2.5) on 10 Greek prompts; pick by quality and speed.
- Stream tokens; cap local answers at about 300 tokens.
- Warm up on startup and keep the model loaded (`keep_alive`).
- The employee simulator never calls the local model; it uses stub responses.
- Timeout (configurable, e.g. 20 s) with a friendly message instead of hanging.
- Optional `OLLAMA_HOST` env var to use a host-native Ollama (GPU/Metal on Mac); the default stays inside compose.

**Fast and robust first start (P0 rules, not optional)**
- The local model is never on the critical path: `docker compose up` reaches healthy, the dashboard is seeded and the chat works before and without the model. The UI shows "Local assistant loading: 60%" until it is ready. If the download fails, confidential content falls back to block with explanation, with no error shown.
- Runtime choice, decided Sat 14 by measurement: the official llama.cpp server image (CPU, small, one GGUF file from Hugging Face, OpenAI-compatible API) versus `ollama/ollama` (larger image). LiteLLM config is the same either way.
- No PyTorch in images: embeddings and the injection classifier run on ONNX (fastembed or onnxruntime). Brain image target: a few hundred MB.
- Slim images: `python:3.12-slim`, multi-stage builds, `nginx:alpine` for the web app, no node_modules in final images.
- CI pushes images to GitHub Container Registry; compose uses them as `cache_from` so a judge's `--build` reuses layers. A from-scratch build must still pass in CI.
- Smallest model that passes the Greek quality check (1B in 4-bit is about 0.8 GB).
- Tests before submission: start with no internet after the build; start with Hugging Face blocked; start with no OpenAI key. The app must open in all three.
- README setup section opens with measured numbers: first-start download size, time, RAM needed, and that the local model is optional.

Go/no-go on Sat 14: measure time to first token and tokens per second on a mid-range Windows laptop and on a Mac. If unacceptable even with the smallest model, the default action for confidential content becomes block with explanation and an approved alternative, and local answering becomes an opt-in setting. Pitch line either way: in production the model runs on a GPU server inside the company network; only one URL changes.

## 22. README outline (required parts first)

1. Video link and one-line pitch
2. Concept
3. Main features
4. Setup and run (one command, requirements incl. RAM, optional OpenAI key, ports, demo logins)
5. Architecture (diagram + services table)
6. Evaluation results (from `eval/report.md`)
7. Privacy and governance (GDPR, AI Act)
8. Known limits
9. Roadmap (future usage)
10. Team

## 23. Milestones (acceptance = demoable from clean clone)

| Date | Done when |
| --- | --- |
| Fri 13 | Compose starts all services healthy; CI green with smoke test |
| Sat 14 | Personal keys work; pattern checks mask and unmask in Company Chat. Go/no-go: paraphrase recall measured on 20 el+en paraphrases |
| Sun 15 | Document checks, warn and block, normalisation, file upload; `gen_org.py` builds the synthetic organisation; logs ingested, inventory shows hidden tools |
| Mon 16 | Dashboard: incidents, policy editor; local-model routing |
| Tue 17 | Session memory + puzzle view; DNA copies + attribution; onboarding page; employee simulator |
| Wed 18 | `make eval` with targets; analyst presets; injection checks; MCP if time. Feature freeze 18:00 |
| Thu 19 | Platform matrix test; Playwright + axe green; README final; video recorded. Code freeze 20:00 |
| Fri 20 | Submit by midday |

Go/no-go fallback (Sat 14): if paraphrase recall is weak, try `intfloat/multilingual-e5-base`, smaller chunks; if still weak, DNA becomes P2 and the story leads with gateway + local routing + cross-prompt tracking.

## 24. Conventions

- Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2; TypeScript strict.
- Small PRs into `main`; `main` must always pass `docker compose up --build`.
- Commit messages in English, imperative. Do not add Claude attribution lines (no Co-Authored-By, no "Generated with Claude Code") to commits or PRs.
- No secrets in code, logs or fixtures. Masked previews only.
- Every user-facing message: plain language, says what happened and what to do next.
