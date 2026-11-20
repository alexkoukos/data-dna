# Architecture

How Sentry is built, how a prompt is decided, and how the system protects the data it inspects. The code is the source of truth; file paths are given so each claim can be checked.

## 1. System

```
 Employee --> web (React) ---------+
 SDKs, agents, Claude Code --------+--> gateway (LiteLLM) --> cloud model | local model
 Browser extension (chatgpt.com) --+        |  pre-call and post-call guardrail
                                            v
                                        brain (FastAPI) --> db (Postgres 16 + pgvector)
                                            |
                                            +--> vault-a, vault-b (split storage)
```

| Service | Role | Port |
| --- | --- | --- |
| `web` | React + TypeScript + Tailwind app: Company Chat, security view, Try to break it. Served by nginx. | 3000 |
| `gateway` | LiteLLM proxy with a custom guardrail (`infra/gateway/dna_guardrail.py`) that calls the brain before and after every model call. **Fails closed**: if the brain is down, nothing passes. | 4000 |
| `brain` | Detection pipeline, policy engine, incidents, analyst questions, API docs at `/docs`. | 8001 |
| `db` | Postgres 16 with pgvector. Seeded with a synthetic company. | internal |
| `vault-a`, `vault-b` | Two separate Postgres instances for split storage (section 5). | internal |
| `ollama` | Optional local model (`make local`). Without it, "answered locally" returns a stand-in answer. | 11434 |

`docker-compose.yml` starts everything with health checks; `brain` waits for the database and both vaults. Ports bind to `127.0.0.1`. With no `OPENAI_API_KEY` the demo models `demo-mock`, `demo-echo` and `demo-leaky` answer offline.

## 2. Request flow

1. A client calls the gateway with a personal key. LiteLLM resolves the key to a user and team.
2. The `pre_call` guardrail sends the whole request to `POST /v1/inspect`: every earlier turn, system prompt, tool descriptions and tool results, not only the last message.
3. The brain runs the pipeline (section 3) and returns a decision with reasons, masked messages and an incident id.
4. The gateway acts on the decision:

| Outcome | What the gateway does |
| --- | --- |
| **allow** | Forwards the request unchanged. |
| **mask** | Forwards the masked text. The `post_call` hook restores the person's own values in the answer (`POST /v1/unmask`). |
| **warn** | Returns HTTP 409 with the reasons. The client retries with `X-DNA-Ack: <reason>` to proceed. The acknowledgement is remembered for 1 hour per personal key. |
| **local** | Routes to the local model. The data never leaves the company. |
| **block** | Returns HTTP 403 with the reasons and an approved alternative. |

5. The answer is checked too (`POST /v1/inspect-output`, streamed or not): echoed secrets and identifiers are masked, and an answer that reproduces a protected document is withheld. Tool results go through `POST /v1/inspect-tool-result`.
6. Every non-allow decision writes an incident. Allow writes only a counter row.

**Files in Company Chat.** The chat sends each attached file to `POST /v1/files/extract` (`brain/files.py`). The brain checks the content by magic bytes (PDF, DOCX, PNG/JPG and other images, UTF-8 text), reads images and scanned PDF pages with OCR (RapidOCR, ONNX on CPU, up to 10 pages per file), applies the size, page (50) and time limits, cuts the text to `FILE_MAX_CHARS`, and returns it without storing or logging it. The chat then puts the text inside the user message (`[File: name] … [End of file: name]`), so it reaches the model only through the gateway and `/v1/inspect`, like typed text. `/v1/inspect` also runs the stamp check (RESTRICTED, CONFIDENTIAL…) on each file block and names the file in the reason. **Pictures.** An image is read the way a vision model would see it (`documents/ocr.py`, `read_image`): OCR on the picture as shown (on white, and on black when it has transparency), on a local-contrast copy (CLAHE) that brings out near-invisible text, on the colour channels with transparency removed, and on turned copies when text runs vertically; QR codes and barcodes are decoded (OpenCV) and free-text metadata is read (PNG text, XMP, EXIF). Text found only by the extra passes is labelled hidden, and that label is a finding of its own (`hidden_text`, block by default). The injection phrases also match OCR's typical slips (a lowercase l for I, words run together). In Company Chat an attached picture is also sent to the model as an image part: the browser redraws it on white (at most 2048 px, JPEG), which drops metadata and anything under transparency, and the gateway checks that exact image. File text is introduced as material, not instructions, and marker lines inside it are quoted so a file cannot close its own block. Inline files sent straight to the gateway (SDKs, agents) take the other road: the hook forwards them to `/v1/inspect` as `attachments`, the brain reads them the same way, and a file it cannot read is refused (`infra/gateway/dna_inspect.py`, `media_attachments`).

"Send it to Company AI instead" resends a stopped message with `X-DNA-Reroute: 1`; the brain masks what must be masked and answers `local`. Injection, decoy credentials, document rebuilds and attached files are never rerouted. Setup for clients, with the exact variables: [GATEWAY_SETUP.md](GATEWAY_SETUP.md).

## 3. Detection pipeline

Cheapest first (`services/brain/src/brain/detection/pipeline.py`). When a cheap check already decides to block, the slow model checks are skipped. A prompt that needs no LLM at all is the normal case: 100% of the evaluation set.

| Level | What it does | Code |
| --- | --- | --- |
| 1. Clean-up | Unicode normalisation; strips zero-width and bidi characters; folds look-alike letters (Greek/Cyrillic inside a mixed-script word), digits from other scripts, spaced digits; decodes hex, percent and HTML-entity text. Every trick found is recorded as an evasion signal. | `normalize.py`, `confusables.py`, `greeklish.py` |
| 2. Decoy credentials | Exact match of planted honeytokens. A hit means that document has leaked. | `honeytokens.py` |
| 3. Identifiers | AFM, AMKA, IBAN, cards with checksums; ADT, plates, Greek phones, passport and GEMI next to their names. | `patterns.py`, `validators.py` |
| 4. Secrets and code | Key and credential rules (YARA), source-code fingerprints (winnowing). | `yara_rules.py`, `code_fingerprint.py`, `rules/` |
| 5. Prompt injection | Phrase heuristics (English, Greek, Greeklish) plus an optional classifier (`protectai/deberta-v3-base-prompt-injection-v2`, ONNX, `make injection-model`). | `injection/` |
| 6. People | Names, emails, phones (surname endings and a surname list, no model call). | `entities.py` |
| 7. Client names | Accent- and case-insensitive match against the client list. | `entities.py` |
| 8. Documents | Registered confidential documents, matched even when reworded (section 4). | `documents/` |

Session memory (`documents/session.py`) tracks which parts of a restricted document a person has already sent within 24 hours. At 40% coverage, or 3 prompts hitting one restricted document, the next one blocks. This catches a document rebuilt piece by piece.

Every decision stores the list of levels that fired (`trace.py`). The incident page shows it as "Why this decision"; it holds entity names and masked previews, never the prompt.

## 4. Document matching

Documents are registered as fingerprints, not text.

- **Chunking.** 16-word windows, step 8 (`documents/chunking.py`).
- **Copies and near copies.** MinHash with Jaccard of at least 0.5.
- **Paraphrases.** Embeddings with `multilingual-e5-small` (ONNX, 384 dimensions) in pgvector. Cosine cutoff 0.88, found by sweeping a labelled set (`make calibrate`, [calibration.md](calibration.md)). A document can carry translations (`name.en.md` beside `name.md`); those use a stricter 0.90 so English rewrites of a Greek document are caught without extra false alarms.
- **Certainty.** A rewrite of a restricted document scoring 0.91 or more blocks. Below that it is answered by the local model, so a wrong guess costs a slower answer, not a refusal (`HIGH_CONFIDENCE` in `pipeline.py`).
- **Copy attribution (DNA).** Each recipient's copy carries 6 to 8 small decoy details (a codename, a reference) with 4 variants each, never touching dates, amounts or legal terms (`dna/marks.py`). A leak that matches k marks names its copy; the chance of a coincidence is (1/4)^k.

## 5. Policy engine

`policy/engine.py`. Precedence: block > local > warn > mask > allow. The defaults in `policy/policies.yaml` seed the database; after that the database is the source of truth and the Policies page edits it.

| Finding | Default |
| --- | --- |
| Greek identifier, IBAN, card, secret, person contact | mask |
| Client name, source code | warn |
| Prompt injection, decoy credential | block |
| Document: internal, confidential | answer locally |
| Document: restricted | block |

- **Shadow mode.** Records what the policy would have done and changes nothing.
- **Try before saving.** `POST /v1/policies/preview` replays the last 14 days against a proposed table.
- **Group exceptions.** Per-team and per-role rules (`policy/groups.py`).
- Policy changes and shadow-mode switches go to the audit log.

## 6. Shadow AI discovery

Proxy and DNS logs (Squid `access.log`, Zeek `dns.log`; synthetic here) are matched against the `ai_tools` catalogue (`data/ai_tools.csv`): each tool is approved, tolerated or unapproved, with a risk level and an approved alternative. Gateway traffic counts as the approved "Company AI" tool. Employees can request a new tool in Chat; security approves or rejects it with a risk rating (`toolrequests.py`).

## 7. Analyst questions

`/security/ask`. Reviewed questions run fixed, read-only SQL with no model (`ask/presets.py`); the first is the brief's own, "Which teams sent client data to unapproved AI tools this week?". Free text goes to a model through a checker that allows one `SELECT` over three views (`v_incidents`, `v_tool_usage`, `v_inventory`) and shows the SQL (`ask/free.py`). A typed copy of a reviewed question uses the reviewed SQL.

## 8. Data model

Defined in `services/brain/src/brain/db/tables.py`; init scripts in `infra/db/`.

| Group | Tables |
| --- | --- |
| People | `users`, `api_keys`, `clients` |
| Documents | `documents`, `doc_chunks`, `doc_marks`, `doc_copies`, `honeytokens`, `session_coverage` |
| Decisions | `incidents`, `reveal_requests`, `counters_daily`, `settings` |
| Tools | `ai_tools`, `tool_usage_daily`, `tool_requests` |
| Red team | `breakit_candidates` |
| Audit | `audit_log` (append-only) |

## 9. Web app and extension

- **Web** (`web/`): Company Chat (with file upload), Connect (personal keys), Try to break it, and the security area: overview, AI tools, incidents, documents, policies, groups, history, impact, break-it review, weekly digest, ask. Tokens are in `web/src/index.css`.
- **Extension** (`extension/`, Manifest V3, plain JavaScript): checks paste and send on `chatgpt.com` through `POST /v1/extension/inspect`, `/ack` and `GET /v1/extension/me`. The brain allows browser calls only from `chrome-extension://<EXTENSION_ID>`. It fails open if the gate is unreachable and closed if the text is refused as too long. Only text is checked; one site is covered.
- **MCP proxy** (`scripts/mcp_proxy.py`): Model Context Protocol traffic through the same checks.
- **SIEM** (`docs/siem/`): `GET /v1/export/incidents` (JSON lines), optional CEF syslog and HMAC-signed webhook. Events never carry prompt text or masked previews.

## 10. Protecting the data Sentry inspects

A watcher must keep little. Each claim below has a test that fails if it stops being true (`services/brain/tests/test_privacy_claims.py`).

| Claim | Code | Test |
| --- | --- | --- |
| No raw prompt is stored. Incidents keep categories, reasons, a masked preview and a trace of check names. | `records.py`, `db/tables.py` | `test_a_raw_prompt_is_in_no_table_after_mask_warn_block_shadow_and_allow`; `test_no_table_has_a_text_column_that_could_hold_a_raw_prompt` |
| Only masked previews are shown. | `records.py`, `detection/patterns.py` | `test_the_masked_preview_is_the_only_prompt_derived_column_on_an_incident` |
| A real name needs two people: one asks with a reason, a different one approves. | `reveal.py` | `test_identity_stays_sealed_until_a_second_person_approves` |
| Sensitive actions are audited (reveals, policy edits, setting changes, decoy triggers). | `reveal.py`, `policy/store.py` | `test_update_changes_current_and_writes_audit` |
| Incidents are deleted after `RETENTION_DAYS` (default 30). | `insights.py` (`purge_expired`) | `test_purge_deletes_old_incidents_and_their_reveal_requests` |
| Shadow-mode changes are audited. | `settings_store.py` | `test_shadow_mode_off_enforces_again_and_the_change_is_audited` |

Also: keys live in `.env` only (gitleaks in CI); model answers are checked before the person sees them; the free-text analyst question is read-only over three views; Try to break it stores nothing but counters and a masked preview, and a submitted miss is a review-queue row until a security user decides.

### Split storage

`brain/splitstore/`. The most sensitive fields (salaries, names) are never stored whole.

- **Splitting.** Numbers are integer cents mod `P = 2^127 - 1`: `share_a` is random and `share_b = (value - share_a) mod P`. Text is XOR-split with a random pad (UTF-8, so Greek works). A dump of one vault is random noise.
- **Isolation.** `vault-a` and `vault-b` have their own credentials, volume and internal network. Only `brain` reaches both. The app role is not a superuser and has SELECT/INSERT/UPDATE/DELETE on two tables only.
- **Integrity.** Three HMAC-SHA256 tags bind record and field, so a moved, changed or missing share is detected and audited. The key lives in an app-only volume and is generated on first start.
- **Atomic writes.** Two-phase commit across both vaults, with a background check that settles leftovers.
- **Reveal.** Allowed roles only (`admin`, `dpo`, `payroll`), every call audited without values. `aggregate_sum` adds values by summing inside each vault, so no single value is rebuilt.
- **HTTP routes** (`/v1/vault/*`) are off until `VAULT_API_TOKEN` is set.

Run it: `make split-demo` (seed, dump one vault, aggregate, tamper) and `make split-test`.

## 11. Limits

What Sentry does not stop, and the threat model behind it: [THREAT_MODEL.md](THREAT_MODEL.md). Measurements: [EVALUATION.md](EVALUATION.md).
