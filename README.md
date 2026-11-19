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
- **Attack set (X2).** `data/eval/attacks.csv` holds 80 red-team prompts (invisible characters, look-alike letters, hex, URL, ROT13, reversed, spaced, leetspeak, prompt injection, document rewrites, secrets, combined tricks, and normal prompts that must not be flagged). `make eval` reports how many are handled and lists the misses honestly: 80 of 80 today, after the seven known gaps were fixed.
- **More Greek identifiers (X6).** Police ID (ADT), number plates, Greek mobile and landline numbers (with or without +30), and, next to their names, passport and GEMI numbers are found and masked. They have no checksum, so a few look-alikes such as "TAX 1234" can match a plate shape; the cost is one needless mask.
- **Answer check (X7).** What a model says is checked before the person sees it: echoed secrets and identifiers are masked (patterns and YARA rules), and an answer that reproduces a protected document is withheld whole.
- **Try a policy first (X12).** On the Policies page, "Try on the last 14 days" shows how many past incidents a change would have made stricter or looser, before you save. It replays the stored categories and matched document, so no raw prompt is ever kept.

## Setup and run
Requirements: Docker with Compose v2, about 2 GB of free RAM for Docker, and ports 3000, 4000 and 8001 free.

Measured on Linux (amd64, Docker 15 GB, 19 Nov 2026, images already built, fresh volumes):

| What | Result |
| --- | --- |
| Start until all six services are healthy (`make up` after `make reset`) | 78 s |
| RAM when idle for 2 minutes (six services) | about 1.7 GB: brain 881 MB, gateway 712 MB, database 67 MB, vault-a 22 MB, vault-b 21 MB, web 5 MB |
| Web (3000) and API docs (8001) answer | yes, HTTP 200 |

The first build from scratch downloads the models and takes several minutes; macOS (arm64, OrbStack) measured 72 s to build and 48 s to start on 13 Nov, before the vaults were added. Windows (WSL 2) is not measured.

```bash
git clone <this repo>
cd data-dna
cp .env.example .env        # optional: add OPENAI_API_KEY
docker compose up --build
```
Open http://localhost:3000 (app) and http://localhost:8001/docs (API).

**Demo access.** There is no login. Get a personal key on the Connect page (`/connect`). The offline demo models are `demo-mock`, `demo-echo` and `demo-leaky`, so everything works without an OpenAI key.

## Split storage (additive secret sharing)
Sensitive fields (salaries, names) are never stored whole. Each value is split into two shares kept in two separate Postgres vaults, so a dump of one vault is random noise.

- **Splitting.** Numbers are integer cents mod `P = 2^127 - 1`: `share_a` is random, `share_b = (value - share_a) mod P`, decoded centered so negatives work. Text and bytes are XOR-split with a random pad (UTF-8, so Greek works).
- **Isolation.** `vault-a` and `vault-b` have their own credentials, volume and `internal` network. Only `brain` is on both; the vaults cannot see each other. `brain` starts only when both are healthy. Schema: `infra/vault/init.sql`.
- **Integrity.** Three HMAC-SHA256 tags: `tag_a` (in vault-a), `tag_b` and `value_tag` (in vault-b). The key lives in the app-only `keys` volume and is never in a vault. `reveal` checks both share tags, rebuilds the value, checks `value_tag` (constant-time compares) and on any mismatch raises `IntegrityError` and writes an audit event. Tags bind `record_id` and `field`, so moving a share to another record fails.
- **API** (`brain.splitstore`): `store(record_id, field, value)`, `reveal(record_id, field, actor)` (roles `admin`, `dpo`, `payroll`; every call, allowed or not, goes to `audit_log`, never with values) and `aggregate_sum(field, record_ids=None, verify_tags=True)` (each vault sums its own shares, only the two sums are combined). By default the aggregate also checks every share against its own tag (`tag_a` / `tag_b`), so a changed, swapped or missing share is caught there too; no value is rebuilt. `verify_tags=False` sums inside the vaults instead (faster, no tag check). `value_tag` needs the whole value, so only `reveal` checks it.
- **Atomic writes.** `store` uses two-phase commit (`PREPARE TRANSACTION`, enabled on both vaults), so either both shares land or neither. If the app dies between prepare and commit, a failed write and a background check (every 60 s) settle the leftovers: prepared in both -> commit both; only in vault-b -> commit; only in vault-a -> roll back. Only entries older than 30 s are touched, so it is safe with several app instances. Until settled (up to about 90 s), a write to the same record waits.
- **Wrong key is not "tampering".** vault-b keeps a canary (`HMAC(key, "canary")`, which says nothing about the key). On first use the app compares it with the current key and raises `KeyMismatchError` with a clear message, instead of every reveal failing as if attacked.
- **HTTP** (off by default; for a trusted backend, since the app has no login yet): set `VAULT_API_TOKEN` (`openssl rand -hex 32`) in `.env`, then call with `Authorization: Bearer <token>`:
  `POST /v1/vault/store` `{record_id, field, value}` (value is an integer in cents or a string), `POST /v1/vault/reveal` `{record_id, field, actor, role}`, `POST /v1/vault/aggregate` `{field, record_ids?, verify_tags?}`. Answers: 401 bad token, 503 off or vaults down or key mismatch, 403 role not allowed, 404 no such value, 409 integrity error, 422 bad input. The role is taken from the request, so only a backend you trust should hold the token; the store still enforces the role list and audits every call.
- **Least privilege.** Each vault has an admin account (`VAULT_*_ADMIN_USER`, used only at first start to load the schema and create the app role) and the app role (`VAULT_*_USER`): not a superuser, cannot create anything, only SELECT/INSERT/UPDATE/DELETE on its two tables. The app role settles its own prepared transactions, so no superuser is needed at run time.
- **Limits.** The sum must fit in about +/-1.7e38. The role and schema are created on a fresh volume only: after pulling this change run `docker compose down -v` (or `make reset`) once, which deletes demo data in the vaults.

Key: nothing to set up. On first start the brain generates the HMAC key once into the app-only `keys` volume (mode 600), so a plain `docker compose up --build` works on a fresh clone. To use your own key, set `HMAC_KEY_FILE` in `.env` to a file inside a volume you mount into the brain (compose override). `make reset` drops the vaults and the key together; if you keep the vaults but lose the key, copy the old key file into the `keys` volume. Switching keys while vault data exists is reported as `KeyMismatchError`.

```bash
docker compose up --build -d --wait                          # whole stack, both vaults included
docker compose --profile test run --rm --build splitstore-tests   # tests, inside the containers
docker compose run --rm brain python -m brain.splitstore.demo     # seed, dump vault-a, aggregate, tamper
```

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

## Browser extension

Personal ChatGPT in the browser bypasses the gate, so the extension (`extension/`, Chrome or Edge, Manifest V3, plain JavaScript, no build step) checks paste and send on `chatgpt.com` against the gate's own checks through its three extension endpoints, `POST /v1/extension/inspect`, `POST /v1/extension/ack` and `GET /v1/extension/me`, before the text leaves the page.

**Load it (3 clicks)**
1. Open `chrome://extensions`, turn on *Developer mode*, press *Load unpacked* and choose the `extension/` folder.
2. Copy the extension ID shown on its card (or on the Settings page), put it in `.env` as `EXTENSION_ID=...` and run `make up` again. The brain allows browser calls only from `chrome-extension://<that ID>`.
3. Open the extension's Settings, paste your personal key from the **Connect** page and press Save. The gate address defaults to `http://localhost:8001`.

**What it does.** Allow: nothing. Mask: the composer text is replaced with the masked text and a note names the entity types and the "Why?" reasons. Warn: a card with the reasons and *Send anyway*, which is recorded on the incident like the gate's `X-DNA-Ack`. Block and local: the send is stopped and the card offers *Use Company AI*. Every non-allow decision is an incident with the tool "ChatGPT (personal)" and channel `browser`, so the Shadow AI view shows it was intercepted. In shadow mode (X11) nothing is changed or stopped; it is only recorded. The user is the owner of the key, resolved by the brain through the gateway; the extension never sends a user or team. The extension stores only the key, the gate address and a daily counter for its popup, and makes no network calls except to the gate address.

**Limits.** One site (`chatgpt.com`); other sites and the ChatGPT desktop or phone apps are not covered, and a person can disable or remove the extension (the Squid and Zeek logs still see that). Only text is checked: pasted images and file uploads are not. If the gate cannot be reached (offline, 502, 503, 504, 429) the extension **fails open**: nothing is blocked and a small badge says so, and nothing is recorded. If the gate answers but refuses to read the text (too long, over 100,000 characters, or malformed) it **fails closed**: the card says "Too long: shorten it or use Company AI". ChatGPT changes its page often, so the composer and send-button selectors in `extension/content.js` may need an update. The test (`web/e2e/extension.spec.ts`) runs against a saved composer page, `extension/test/fixture.html`, not the live site.

## Evaluation
How accuracy is measured: a labelled synthetic set of 195 prompts (`data/eval/prompts.csv`: copies, edits, paraphrases, patterns, split leaks and clean prompts, in Greek and English), scored against a regex-and-keyword baseline, plus two attack sets of 80 each (`data/eval/attacks.csv`, `attacks_scripts.csv`) and a red-team run. The expected answer is written before the result is looked at, so known gaps stay in the files. All data is invented.

Measured on 19 Nov 2026 (`make eval`, `make loadtest`, `make redteam`; full tables in `eval/report.md` and `eval/redteam/report.md`, both committed):

| What | Result | Target |
| --- | --- | --- |
| Paraphrased document leaks found | 100%, 40 of 40 (baseline 5.0%; tuned on this set) | 80% |
| False alarms on clean prompts | 2.1% | 5% |
| Added latency, brain only, one request at a time (p50 / p95) | 19.4 / 67.4 ms | p95 under 100 ms |
| Latency under load, 3 people for 15 s (`make loadtest`), three runs | p50 about 110 ms, p95 316 to 326 ms, 0 errors | p95 under 100 ms: **missed** |
| Latency under load with 3 earlier turns per request (`loadtest.py --history 3`) | p50 484 ms, p95 666 ms | not a target; a fresh long conversation costs more (see below) |
| Prompts needing zero LLM tokens | 100% | 90% |
| Correct copy named when a document leaks | 99.2% | 90% |
| Greeklish, look-alike and foreign-digit attacks caught (X5) | 100% | 80% |
| Attack set `attacks.csv` handled as expected | 80 of 80 | |
| Attack set `attacks_scripts.csv` as expected | 80 of 80 | |
| promptfoo curated cases (`make redteam`) | 25 of 25 | |

The load-test target is missed on this machine: with three people at once the single brain process queues requests, so p95 is about three times the target even though one request alone is well under it. With earlier turns in the request each earlier message costs an embedding and a people-and-contact call, which is why p95 is higher still; those results are remembered per person for 30 minutes, so only the first request of a long chat is slow (a fresh 300,000 character history takes about 7 s, and one that needs more than the per-request allowance is refused with "too long to check" until a retry has worked through it). `make eval` itself passes its latency target (it measures one request at a time).

The misses are listed by id in `eval/report.md` and in `docs/BRIEF_MAP.md`. The load-test p95 sits on the target: 4 of 5 runs passed, by a few milliseconds. Unit tests: 874 brain tests at 88% coverage, 114 web tests and 5 extension tests (`make check`); 40 live gateway tests (`make test-gateway`); 64 end-to-end and accessibility specs (`make e2e`).

## Privacy and governance

### What Pyli itself stores
A watcher must keep little: masked previews and entity names instead of prompts, fingerprints instead of document text, pseudonyms with a two-person reveal and audit log, 30-day retention, local answers for confidential content, and split storage for the most sensitive fields. Plain-language page on GDPR, NIS2 and the EU AI Act (not legal advice): [docs/business/privacy-and-regulation.md](docs/business/privacy-and-regulation.md). Article table: [compliance-mapping.md](docs/business/compliance-mapping.md).

## Business case
Market and cost figures with sources: [market.md](docs/business/market.md). Competitors: [competitors.md](docs/business/competitors.md). SWOT: [swot.md](docs/business/swot.md). Customer, price and sales path (all hypotheses): [customer-and-pricing.md](docs/business/customer-and-pricing.md). Why people will use it: [engagement.md](docs/business/engagement.md). Honest limits: [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).


**Break it (X28).** Practice on `/break-it` is never stored and never creates an incident; only counters, a masked preview, the attack kind and an optional nickname (no login, nothing that identifies a person) are kept, in memory. The one exception is the "It got through" button: the person chooses to submit the exact text as a test case, and the button says so. That raw text lives only in a review-queue row until a security user decides. Approve moves it into `data/eval/attacks_scripts.csv` and blanks the row; reject deletes the row at once.
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
- **Detection is probabilistic.** Both attack sets and the 40 paraphrases pass on our own files, but the fixes were written after seeing the failures, so new forms of attack can still pass. What we know gets through: many model-attack prompts from garak that carry no company data and still reach the model (the gateway flagged only 4 of 27 in one family, 5 of 40 in another). A clean Greek prompt was sent to the local model (P0159). See `docs/BRIEF_MAP.md`.
- **Meaning without matching words** can pass; a paraphrase of a restricted document that scores below 0.91 goes to the local model rather than being blocked, to avoid false blocks; 0.91 or above on a restricted document is blocked (demo step 3 shows 91%). A document can carry translations (`name.en.md` next to `name.md`) so rewrites in another language are compared with text in their own language; that is how Greek salary bands are protected against English rewrites. Translations have to be supplied for each document and language.
- **Slow leaks** beyond the session window, and anything retyped by hand or photographed, are not caught.
- **No login.** The brain API is unauthenticated in demo mode and uses a default master key. Do not expose ports 8001 and 4000 beyond a trusted network. Roles, TLS and a key store are roadmap. In demo mode `POST /v1/keys` gives a personal key to any user id, so anything that trusts a personal key (including the tool-request outcomes) is only as strong as that: a demo-only gap.
- **Load test misses its target.** With three people at once p95 is about 320 ms against 100 ms (one request alone: 67 ms). The brain is one process. Linux and Windows start times are not measured on separate machines.
- Details and reasoning: `docs/THREAT_MODEL.md`.

## Extra features

**Try to break it (X1).** Open `/break-it`, type anything you think the gateway will miss and press "Check it". The page shows the outcome, the reasons and the eight levels of the pipeline in order, with the ones that found something marked. Nothing typed there is stored and nobody's practice shows up as an incident. A starter button per kind of attack comes from `data/eval/attacks_scripts.csv`. `web/e2e/break-it.spec.ts` types ten evasions into the real page and checks each one is stopped.

**Attack file (X2).** `data/eval/attacks_scripts.csv` (next to the technique-based `attacks.csv`) holds 80 invented attacks in 10 kinds (spaced out, encoded, look-alike letters, foreign digits, Greeklish, injection, hidden keys, rewritten documents, decoys, and 8 harmless look-alikes), each with the decision we expect. The expectation is written before looking at the result, so known gaps stay in the file and `make eval` lists them under "Script and decoy attacks" (none left today; the seven that were open are fixed and listed in `docs/BRIEF_MAP.md`). Rows come from `scripts/gen_attacks_scripts.py`; to add your own, append rows to the CSV and do not re-run the generator, or add them to the script.

**Decoy credentials (X4).** A confidential document can carry fake keys and mailboxes that exist nowhere else (`honeytokens:` in its header, or `POST /v1/documents/{id}/honeytokens`, which returns lines to paste in). If one appears in a prompt the decision is block, the reason names the document ("that document has left the company"), the incident is linked to it and `audit_log` gets `honeytoken.triggered`. Matching is an exact string compare against random 20 to 40 character values, so ordinary text and look-alike keys never trigger it (tested on 400 random keys). The three demo documents carry two decoys each. The new category `honeytoken` is on the Policies page and defaults to block.

**Greeklish and look-alike characters (X5).** Before any check the text is cleaned of tricks that keep its length: digits from other scripts (Arabic-Indic, Devanagari, Thai) become 0 to 9, Greek or Cyrillic letters inside a word that mixes scripts or holds a number are folded to the matching Latin ones (a mostly Greek word goes the other way), a capital O or a lower-case l in a long number is read as 0 or 1, and hex, percent-encoded and HTML-entity text is decoded. Names such as "giorgos papadopoulos" are found by Greek surname endings and a list of common surnames, with no model call. `make eval` reports the attacks of these three kinds as one target: 96.2% caught against a target of 80%. A Greek surname with no common ending (for example "Papadaki" in capitals) is still missed.

**Request an AI tool (X29).** Brief question 4 becomes a workflow. In Company Chat, "Request approval" (also offered after a blocked message) asks for a tool with a reason for the person's team. In Security, AI tools, the **Requests** tab lists waiting requests; security picks a risk rating (low, medium, high), the data categories the tool may receive and an optional approved alternative, then approves or rejects, with their name for the audit log. Approving sets `ai_tools.approval` to approved and stores the risk, alternative and allowed categories, so the inventory and "risk per tool" in the ROI view change at once; a tool that was never seen is added. `tool.request`, `tool.approve`, `tool.reject` and `tool.outcome_seen` go to `audit_log`. The requester sees the decision once, as a note above the chat, on their next message. A person can have at most 5 requests waiting. Tests: `services/brain/tests/test_x29_tool_requests.py`, `web/src/pages/ToolRequests.test.tsx`. Allowed categories are recorded and shown on the tool; the detection policy itself is not changed by an approval.
**Break it leaderboard and growing attack set (X28).** `/break-it` also shows today's attempts, how many were stopped, how many got through and the catch rate, plus a top-breakers list by nickname. When an attempt passes but should not have, "It got through" lets the person pick the expected decision (mask, warn or block) and the kind, and sends it to the **Break it review** tab in Security (`/security/review`). Approving appends a row with `source=breakit` and the date to `data/eval/attacks_scripts.csv` (the brain container has that one folder writable); `make eval` then reports those rows on their own line, "Found live, still missed: N", apart from the older attacks. Break it practice still creates no incidents. Tests: `services/brain/tests/test_x28_breakit.py`, `web/src/pages/BreakItBoard.test.tsx`, and `web/e2e/break-it-review.spec.ts` (needs `make up`).
**SIEM export (X30).** How an incident reaches the SOC: `GET /v1/export/incidents?since=...` returns JSON lines, and `.env` can also turn on a syslog sender (CEF, UDP or TCP) and an HMAC-signed webhook that push every new incident. An event holds the time, the user key ID (never the name), team, tool, decision, categories, matched document ID and rule IDs, and never any prompt text or masked preview. `docs/siem/` has a Sigma rule (3 or more blocks for one user in 10 minutes) and Splunk and Elastic examples. `make siem` starts a demo syslog receiver (compose profile `siem`) so the events can be watched arriving. Tests: `services/brain/tests/test_x30_siem.py`.
**Send it to Company AI instead (X31).** Brief question 4 ("suggest an approved alternative") becomes one click. When Company Chat blocks or warns, "Send it to Company AI instead" resends the same message with the header `X-DNA-Reroute: 1`. The brain re-checks it, masks what must be masked and answers `local`, so the gate sends it to the company model and never to the destination that was stopped. The answer shows "Answered by Company AI" and the person's own masked values are restored in it. The incident they just caused changes to **rerouted** (no second incident); "rerouted" counts as stopped in the ROI view and appears in the incident filter and the compliance evidence. Some stops cannot be rerouted and stay blocked: prompt injection, decoy credentials, rebuilding a document over several messages, attached files, and any request type other than chat. Shadow mode never reroutes. Tests: `services/brain/tests/test_x31_reroute.py`, `web/src/pages/Reroute.test.tsx`. The browser extension's block card still links to Company AI rather than sending the text there, so no text leaves the page by URL.
**Weekly team digest (X32).** Brief question 4 also says "warn and educate", so the **Digest** tab in Security (`/security/digest`) gives each team lead one page for the last 7 days: incidents per outcome and per kind of data, the top tools and whether they are approved, the trend against the week before, and two or three short "do this instead" tips picked from the kinds of data that fired (fixed templates in `services/brain/src/brain/digest.py`, no model call). "Copy as email" puts a subject and body on the clipboard and "Download Markdown" saves the same text; nothing is emailed. Data minimisation: the page says at the top that it has team-level counts only, and the SQL reads the views `v_incidents` and `v_inventory` without the column that names the user, so no name, pseudonym, message text or masked preview can appear. "This week" ends at the newest incident, so the seeded demo week is shown. API: `GET /v1/digest/teams`, `/v1/digest?team=`, `/v1/digest.md?team=`. Tests: `services/brain/tests/test_x32_digest.py` (counts match the seeded incidents, no names or text), `web/src/pages/security/Digest.test.tsx`.

## Roadmap
Built already: the browser extension and the SIEM export. Next: (1) Slack and Teams, (2) more languages, (3) a small-company edition with login and roles. Details and what is already built: [docs/business/roadmap.md](docs/business/roadmap.md).

## Team
Alexandros, Stelios, Vasilis, Konstantinos.

---
For contributors: start with `docs/TEAM_GUIDE.md` and `CLAUDE.md`.
