# Pyli, the gate

Πύλη (πύλη, "the gate"). Every prompt passes the gate. Brand and mascot: [docs/BRAND.md](docs/BRAND.md).

> Video: [link, added Thu 19 Nov]
> Pyli is the gate that every AI tool in the company goes through: it finds which AI tools are used, catches sensitive data before it leaves (even when rewritten), and decides per prompt: allow, warn, mask, answer with a local model, or block.

Netcompany Hackathon Athens 2026, Challenge 3: Shadow AI protection and Data Protection.

## Concept
Companies cannot see which AI tools their people use, and cannot stop a client list, a key or a confidential memo from being pasted into one. Banning the tools does not work: people use them anyway, from personal accounts. Pyli takes the other route. It gives people a safe door, one gateway that every AI tool in the company goes through, and checks each prompt on the way out.

For every prompt Pyli decides one of five things: **allow**, **mask** (hide the sensitive part and still get an answer), **warn** (ask the person to confirm), **answer with a local model** (the data never leaves), or **block**. Every decision comes with a reason in plain words and an approved alternative, and the security team sees all of it with the data protected. It also finds which AI tools are in use, including unapproved ones, from usage logs.

The brief's questions are answered one by one, with the number and the demo step for each, in `docs/BRIEF_MAP.md`. The five-minute demo is in `docs/DEMO.md`.

## Main features
- **One gateway for every AI tool.** Chat, SDKs, agents and Claude Code point at one endpoint (LiteLLM). Connect page: `/connect`. Model Context Protocol traffic can go through the same checks (`scripts/mcp_proxy.py`).
- **Detection, cheapest check first.** Text clean-up, patterns with checksums (Greek tax and social security numbers, IBAN, cards), secret and code rules, people and client names, then confidential-document matching that survives rewording (MinHash, then embeddings), session memory across prompts, and prompt-injection checks. Nothing needs a paid model.
- **Five outcomes with a reason.** Company Chat shows the outcome in words and icon, never colour alone. The incident page has a "Why this decision" panel listing the checks that fired.
- **Shadow AI discovery.** The AI tools page lists every tool seen in usage logs with approved, tolerated or unapproved and the approved alternative.
- **Security view.** Overview, incidents with sealed identities (a real name needs two people), documents and marked copies, policies, teams and roles, history, impact.
- **Ask a question.** Analysts pick a reviewed question (the first is the brief's own: "Which teams sent client data to unapproved AI tools this week?") and see a table and the SQL. Free text goes to a model through a checker that allows only one read-only query over three views; a typed copy of a reviewed question uses the reviewed SQL.
- **Policies you can try first.** Editable table, shadow mode (record what would happen, change nothing), and a 14-day replay before saving.
- **Try to break it.** `/break-it` lets anyone attack the checks and see which level caught it.

### Extra features (see `docs/EXTRA_FEATURES.md`)
- **Why this decision (X23).** Every decision carries a short list of the checks that fired (patterns, rules, injection phrases, people and contact model, client list, document matching with its score, session memory, the policy). It is stored on the incident and shown on the incident page. It holds only entity names and masked previews, never the prompt.
- **Shadow mode (X11).** On the Policies page, one switch lets every message through while the dashboard records what the policy would have done ("would have blocked 12"). Use it for the first weeks in a company. The setting is stored in the database and every change is audited.
- **Compliance report (X17).** The Policies page has a PDF button (`GET /v1/compliance-report.pdf`). It maps what the gateway does to GDPR, NIS2 and the EU AI Act with the live numbers behind each line. It supports a company's own review; it is not legal advice. The same table is in `docs/business/compliance-mapping.md`.
- **Attack set (X2).** `data/eval/attacks.csv` holds 80 red-team prompts (invisible characters, look-alike letters, hex, URL, ROT13, reversed, spaced, leetspeak, prompt injection, document rewrites, secrets, combined tricks, and normal prompts that must not be flagged). `make eval` reports how many are handled and lists the misses honestly: 76 of 80 today.
- **More Greek identifiers (X6).** Police ID (ADT), number plates, Greek mobile and landline numbers (with or without +30), and, next to their names, passport and GEMI numbers are found and masked. They have no checksum, so a few look-alikes such as "TAX 1234" can match a plate shape; the cost is one needless mask.
- **Answer check (X7).** What a model says is checked before the person sees it: echoed secrets and identifiers are masked (patterns and YARA rules), and an answer that reproduces a protected document is withheld whole.
- **Try a policy first (X12).** On the Policies page, "Try on the last 14 days" shows how many past incidents a change would have made stricter or looser, before you save. It replays the stored categories and matched document, so no raw prompt is ever kept.

## Setup and run
Requirements: Docker with Compose v2, about 2 GB of free RAM for Docker, and ports 3000, 4000 and 8001 free.

Measured on macOS Apple silicon (arm64, OrbStack, fresh clone, no build cache, 13 Nov 2026):

| What | Result |
| --- | --- |
| Build from scratch (`docker compose build --no-cache`) | 72 s |
| Start until all four services are healthy | 48 s |
| RAM when idle (web, gateway, brain, database) | about 770 MB (gateway 658, brain 70, database 34, web 9) |
| Web (3000) and API docs (8001) answer | yes, HTTP 200 |

Linux and Windows (WSL 2) are not measured yet.

```bash
git clone <this repo>
cd data-dna
cp .env.example .env        # optional: add OPENAI_API_KEY
docker compose up --build
```
Open http://localhost:3000 (app) and http://localhost:8001/docs (API).

## Architecture
```
 Employee --> web (React) --+
 SDKs, agents, Claude Code -+--> gateway (LiteLLM) --> cloud model, or local model
                                  |  pre-call and post-call checks
                                  v
                              brain (FastAPI) --> database (Postgres + pgvector)
```

| Service | What it is | Port |
| --- | --- | --- |
| `web` | React app: Company Chat, security view, Try to break it (served by nginx) | 3000 |
| `gateway` | LiteLLM proxy with a custom guardrail that calls the brain before and after every model call. Fails closed: if the brain is down, nothing passes. | 4000 |
| `brain` | Detection pipeline, policy engine, incidents, analyst questions, API docs at `/docs` | 8001 |
| `db` | Postgres 16 (official image) with pgvector, seeded with a synthetic company | internal |
| `ollama` | Optional local model, started with `make local`. Without it, "answered locally" returns a stand-in answer. | 11434 |

Full design: `docs/PRD.md` section 7. Threats and honest limits: `docs/THREAT_MODEL.md`.

## Evaluation
How accuracy is measured: a labelled synthetic set of 195 prompts (`data/eval/prompts.csv`: copies, edits, paraphrases, patterns, split leaks and clean prompts, in Greek and English), scored against a regex-and-keyword baseline, plus two attack sets of 80 each (`data/eval/attacks.csv`, `attacks_scripts.csv`) and a red-team run. The expected answer is written before the result is looked at, so known gaps stay in the files. All data is invented.

Measured on 17 Nov 2026 (`make eval`, `make loadtest`, `make redteam`; full tables in `eval/report.md`):

| What | Result | Target |
| --- | --- | --- |
| Paraphrased document leaks found | 97.5%, 39 of 40 (baseline 5.0%) | 80% |
| False alarms on clean prompts | 2.1% | 5% |
| Added latency, brain only (p50 / p95) | 12.6 / 28.4 ms | p95 under 100 ms |
| Latency under load, 3 users for 15 s (`make loadtest`) | p50 58 ms, p95 95 to 101 ms over five runs on a quiet machine (4 of 5 under target), 0 errors | p95 under 100 ms |
| Prompts needing zero LLM tokens | 100% | 90% |
| Correct copy named when a document leaks | 99.2% | 90% |
| Attack set `attacks.csv` handled as expected | 76 of 80 | |
| Attack set `attacks_scripts.csv` as expected | 77 of 80 | |
| promptfoo curated cases (`make redteam`) | 24 of 25 | |

The misses are listed by id in `eval/report.md` and in `docs/BRIEF_MAP.md`. The load-test p95 sits on the target: 4 of 5 runs passed, by a few milliseconds. Unit tests: 365 brain tests at 91% coverage and 79 web tests (`make check`); end-to-end and accessibility checks: 41 specs (`make e2e`).

## Privacy and governance
Pyli inspects what people type, so it holds itself to the same rule it enforces. Each claim below points at the code and at a test that fails if the claim stops being true (`services/brain/tests/test_privacy_claims.py` also checks that every test named here exists).

| Claim | Code | Test |
| --- | --- | --- |
| No raw prompt is stored. Incidents keep categories, reasons, a masked preview and a trace of check names. | `services/brain/src/brain/records.py`, `db/tables.py` | `test_privacy_claims.py::test_a_raw_prompt_is_in_no_table_after_mask_warn_block_shadow_and_allow` sends prompts through every outcome and searches every table and the dashboard API for the raw text. `::test_no_table_has_a_text_column_that_could_hold_a_raw_prompt` fails if any table gains a text column with a prompt-like name that nobody has reviewed. `test_trace_shadow.py::test_the_trace_is_stored_on_the_incident_and_holds_no_raw_value` |
| Only masked previews are shown. | `records.py`, `detection/patterns.py` | `test_privacy_claims.py::test_the_masked_preview_is_the_only_prompt_derived_column_on_an_incident`, `test_x_ops.py::test_try_attempts_are_listed_newest_first_with_masked_previews` |
| A real name needs two people: one asks with a reason, a different one approves. | `services/brain/src/brain/reveal.py` | `test_dashboard_api.py::test_identity_stays_sealed_until_a_second_person_approves`, `::test_denied_request_never_reveals_and_cannot_be_decided_twice` |
| Every sensitive action is in the audit log (reveal steps, policy edits, setting changes, decoy triggers). | `reveal.py` (`_audit`), `policy/store.py` (`audit_table`) | the two reveal tests above, `test_policy_store.py::test_update_changes_current_and_writes_audit`, `test_x4_honeytokens.py` |
| Incidents are deleted after `RETENTION_DAYS` (default 30). | `services/brain/src/brain/insights.py` (`purge_expired`), `records.py` (`expires_at`) | `test_x_ops.py::test_purge_deletes_old_incidents_and_their_reveal_requests`, `test_privacy_claims.py::test_every_stored_incident_has_an_expiry_date` |
| Shadow mode changes are audited. | `settings_store.py`, `main.py` (`put_shadow`) | `test_trace_shadow.py::test_shadow_mode_off_enforces_again_and_the_change_is_audited` |

Other protections: API keys live in `.env` only (gitleaks runs in CI); model answers are checked before the person sees them; the free-text analyst question runs read-only over three views. The compliance report (`GET /v1/compliance-report.pdf`, also in `docs/business/compliance-mapping.md`) maps the gateway to GDPR, NIS2 and the EU AI Act. It supports a company's own review and is not legal advice.

## Known limits
- **Only traffic through the gateway is checked.** Personal devices and tools that bypass it are seen in usage logs, not stopped.
- **Detection is probabilistic.** Measured misses: 4 of 80 and 3 of 80 attacks, one reworded question about the Delphi agreement (P0105), one of 25 red-team cases, and many model-attack prompts from garak that carry no company data and still reach the model (the gateway flagged only 4 of 27 in one family, 5 of 40 in another). A clean Greek prompt was sent to the local model (P0159). See `docs/BRIEF_MAP.md`.
- **Meaning without matching words** can pass; a strong paraphrase goes to the local model rather than being blocked, to avoid false blocks. A document can carry translations (`name.en.md` next to `name.md`) so rewrites in another language are compared with text in their own language; that is how Greek salary bands are protected against English rewrites. Translations have to be supplied for each document and language.
- **Slow leaks** beyond the session window, and anything retyped by hand or photographed, are not caught.
- **No login.** The brain API is unauthenticated in demo mode and uses a default master key. Do not expose ports 8001 and 4000 beyond a trusted network. Roles, TLS and a key store are roadmap.
- **Load test is right at its target** (p95 95 to 101 ms against 100 ms with nothing else running; worse on a busy machine). There is almost no margin. Linux and Windows start times are not measured on separate machines.
- Details and reasoning: `docs/THREAT_MODEL.md`.

## Extra features

**Try to break it (X1).** Open `/break-it`, type anything you think the gateway will miss and press "Check it". The page shows the outcome, the reasons and the eight levels of the pipeline in order, with the ones that found something marked. Nothing typed there is stored and nobody's practice shows up as an incident. A starter button per kind of attack comes from `data/eval/attacks_scripts.csv`. `web/e2e/break-it.spec.ts` types ten evasions into the real page and checks each one is stopped.

**Attack file (X2).** `data/eval/attacks_scripts.csv` (next to the technique-based `attacks.csv`) holds 80 invented attacks in 10 kinds (spaced out, encoded, look-alike letters, foreign digits, Greeklish, injection, hidden keys, rewritten documents, decoys, and 8 harmless look-alikes), each with the decision we expect. The expectation is written before looking at the result, so known gaps stay in the file and `make eval` lists them under "Script and decoy attacks" (today: reversed text, base64 injection, a key split by string concatenation, a surname with no common ending, one rewritten salary table). Rows come from `scripts/gen_attacks_scripts.py`; to add your own, append rows to the CSV and do not re-run the generator, or add them to the script.

**Decoy credentials (X4).** A confidential document can carry fake keys and mailboxes that exist nowhere else (`honeytokens:` in its header, or `POST /v1/documents/{id}/honeytokens`, which returns lines to paste in). If one appears in a prompt the decision is block, the reason names the document ("that document has left the company"), the incident is linked to it and `audit_log` gets `honeytoken.triggered`. Matching is an exact string compare against random 20 to 40 character values, so ordinary text and look-alike keys never trigger it (tested on 400 random keys). The three demo documents carry two decoys each. The new category `honeytoken` is on the Policies page and defaults to block.

**Greeklish and look-alike characters (X5).** Before any check the text is cleaned of tricks that keep its length: digits from other scripts (Arabic-Indic, Devanagari, Thai) become 0 to 9, Greek or Cyrillic letters inside a word that mixes scripts or holds a number are folded to the matching Latin ones (a mostly Greek word goes the other way), a capital O or a lower-case l in a long number is read as 0 or 1, and hex, percent-encoded and HTML-entity text is decoded. Names such as "giorgos papadopoulos" are found by Greek surname endings and a list of common surnames, with no model call. `make eval` reports the attacks of these three kinds as one target: 96.2% caught against a target of 80%. A Greek surname with no common ending (for example "Papadaki" in capitals) is still missed.

## Roadmap
_From docs/business (T5)._

## Team
Alexandros, Stelios, Vasilis, Konstantinos.

---
For contributors: start with `docs/TEAM_GUIDE.md` and `CLAUDE.md`.
