# Pyli, the gate

Πύλη (πύλη, "the gate"). Every prompt passes the gate. Brand and mascot: [docs/BRAND.md](docs/BRAND.md).

> Video: [link, added Thu 19 Nov]
> Pyli is the gate that every AI tool in the company goes through: it finds which AI tools are used, catches sensitive data before it leaves (even when rewritten), and decides per prompt: allow, warn, mask, answer with a local model, or block.

Netcompany Hackathon Athens 2026, Challenge 3: Shadow AI protection and Data Protection.

## Concept
_To be written (R1). Source: docs/IDEA_AND_TEAM.md._

## Main features
_To be written (R1)._

### Extra features (see `docs/EXTRA_FEATURES.md`)
- **Why this decision (X23).** Every decision carries a short list of the checks that fired (patterns, rules, injection phrases, people and contact model, client list, document matching with its score, session memory, the policy). It is stored on the incident and shown on the incident page. It holds only entity names and masked previews, never the prompt.
- **Shadow mode (X11).** On the Policies page, one switch lets every message through while the dashboard records what the policy would have done ("would have blocked 12"). Use it for the first weeks in a company. The setting is stored in the database and every change is audited.
- **Compliance report (X17).** The Policies page has a PDF button (`GET /v1/compliance-report.pdf`). It maps what the gateway does to GDPR, NIS2 and the EU AI Act with the live numbers behind each line. It supports a company's own review; it is not legal advice. The same table is in `docs/business/compliance-mapping.md`.
- **Attack set (X2).** `data/eval/attacks.csv` holds 80 red-team prompts (invisible characters, look-alike letters, hex, URL, ROT13, reversed, spaced, leetspeak, prompt injection, document rewrites, secrets, combined tricks, and normal prompts that must not be flagged). `make eval` reports how many are handled and lists the misses honestly: 77 of 80 today.
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

## Split storage (additive secret sharing)
Sensitive fields (salaries, names) are never stored whole. Each value is split into two shares kept in two separate Postgres vaults, so a dump of one vault is random noise.

- **Splitting.** Numbers are integer cents mod `P = 2^127 - 1`: `share_a` is random, `share_b = (value - share_a) mod P`, decoded centered so negatives work. Text and bytes are XOR-split with a random pad (UTF-8, so Greek works).
- **Isolation.** `vault-a` and `vault-b` have their own credentials, volume and `internal` network. Only `brain` is on both; the vaults cannot see each other. `brain` starts only when both are healthy. Schema: `infra/vault/init.sql`.
- **Integrity.** Three HMAC-SHA256 tags: `tag_a` (in vault-a), `tag_b` and `value_tag` (in vault-b). The key is the compose secret `secrets/hmac_key` and is never in a vault. `reveal` checks both share tags, rebuilds the value, checks `value_tag` (constant-time compares) and on any mismatch raises `IntegrityError` and writes an audit event. Tags bind `record_id` and `field`, so moving a share to another record fails.
- **API** (`brain.splitstore`): `store(record_id, field, value)`, `reveal(record_id, field, actor)` (roles `admin`, `dpo`, `payroll`; every call, allowed or not, goes to `audit_log`, never with values) and `aggregate_sum(field, record_ids=None, verify_tags=True)` (each vault sums its own shares, only the two sums are combined). By default the aggregate also checks every share against its own tag (`tag_a` / `tag_b`), so a changed, swapped or missing share is caught there too; no value is rebuilt. `verify_tags=False` sums inside the vaults instead (faster, no tag check). `value_tag` needs the whole value, so only `reveal` checks it.
- **Atomic writes.** `store` uses two-phase commit (`PREPARE TRANSACTION`, enabled on both vaults), so either both shares land or neither. If the app dies between prepare and commit, a failed write and a background check (every 60 s) settle the leftovers: prepared in both -> commit both; only in vault-b -> commit; only in vault-a -> roll back. Only entries older than 30 s are touched, so it is safe with several app instances. Until settled (up to about 90 s), a write to the same record waits.
- **Wrong key is not "tampering".** vault-b keeps a canary (`HMAC(key, "canary")`, which says nothing about the key). On first use the app compares it with the current key and raises `KeyMismatchError` with a clear message, instead of every reveal failing as if attacked.
- **HTTP** (off by default; for a trusted backend, since the app has no login yet): set `VAULT_API_TOKEN` (`openssl rand -hex 32`) in `.env`, then call with `Authorization: Bearer <token>`:
  `POST /v1/vault/store` `{record_id, field, value}` (value is an integer in cents or a string), `POST /v1/vault/reveal` `{record_id, field, actor, role}`, `POST /v1/vault/aggregate` `{field, record_ids?, verify_tags?}`. Answers: 401 bad token, 503 off or vaults down or key mismatch, 403 role not allowed, 404 no such value, 409 integrity error, 422 bad input. The role is taken from the request, so only a backend you trust should hold the token; the store still enforces the role list and audits every call.
- **Least privilege.** Each vault has an admin account (`VAULT_*_ADMIN_USER`, used only at first start to load the schema and create the app role) and the app role (`VAULT_*_USER`): not a superuser, cannot create anything, only SELECT/INSERT/UPDATE/DELETE on its two tables. The app role settles its own prepared transactions, so no superuser is needed at run time.
- **Limits.** The sum must fit in about +/-1.7e38. The role and schema are created on a fresh volume only: after pulling this change run `docker compose down -v` (or `make reset`) once, which deletes demo data in the vaults.

Key: run `./scripts/gen_hmac_key.sh` (or `make up`, which does it first) to create `secrets/hmac_key`. If you skip it, compose mounts an empty directory there and a plain `docker compose up` still works: the app generates a key once into an app-only volume and logs a warning. That key lives in a Docker volume, so create the real file before storing data you care about; switching keys later is reported as `KeyMismatchError`. If Docker already made the empty directory, the script replaces it (or tells you to `sudo rmdir secrets/hmac_key`, which needs root because Docker owns it).

```bash
docker compose up --build -d --wait                          # whole stack, both vaults included
docker compose --profile test run --rm --build splitstore-tests   # tests, inside the containers
docker compose run --rm brain python -m brain.splitstore.demo     # seed, dump vault-a, aggregate, tamper
```

## Architecture
_Diagram and services table (R1). Source: docs/PRD.md section 7._

## Evaluation
_Results from `make eval` (E1)._

## Privacy and governance
A watcher must keep little: masked previews and entity names instead of prompts, fingerprints instead of document text, pseudonyms with a two-person reveal and audit log, 30-day retention, local answers for confidential content, and split storage for the most sensitive fields. Plain-language page on GDPR, NIS2 and the EU AI Act (not legal advice): [docs/business/privacy-and-regulation.md](docs/business/privacy-and-regulation.md). Article table: [compliance-mapping.md](docs/business/compliance-mapping.md).

## Business case
Market and cost figures with sources: [market.md](docs/business/market.md). Competitors: [competitors.md](docs/business/competitors.md). SWOT: [swot.md](docs/business/swot.md). Customer, price and sales path (all hypotheses): [customer-and-pricing.md](docs/business/customer-and-pricing.md). Why people will use it: [engagement.md](docs/business/engagement.md). Honest limits: [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).


## Known limits
_To be written._

## Extra features

**Try to break it (X1).** Open `/break-it`, type anything you think the gateway will miss and press "Check it". The page shows the outcome, the reasons and the eight levels of the pipeline in order, with the ones that found something marked. Nothing typed there is stored and nobody's practice shows up as an incident. A starter button per kind of attack comes from `data/eval/attacks_scripts.csv`. `web/e2e/break-it.spec.ts` types ten evasions into the real page and checks each one is stopped.

**Attack file (X2).** `data/eval/attacks_scripts.csv` (next to the technique-based `attacks.csv`) holds 80 invented attacks in 10 kinds (spaced out, encoded, look-alike letters, foreign digits, Greeklish, injection, hidden keys, rewritten documents, decoys, and 8 harmless look-alikes), each with the decision we expect. The expectation is written before looking at the result, so known gaps stay in the file and `make eval` lists them under "Script and decoy attacks" (today: reversed text, base64 injection, a key split by string concatenation, a surname with no common ending, one rewritten salary table). Rows come from `scripts/gen_attacks_scripts.py`; to add your own, append rows to the CSV and do not re-run the generator, or add them to the script.

**Decoy credentials (X4).** A confidential document can carry fake keys and mailboxes that exist nowhere else (`honeytokens:` in its header, or `POST /v1/documents/{id}/honeytokens`, which returns lines to paste in). If one appears in a prompt the decision is block, the reason names the document ("that document has left the company"), the incident is linked to it and `audit_log` gets `honeytoken.triggered`. Matching is an exact string compare against random 20 to 40 character values, so ordinary text and look-alike keys never trigger it (tested on 400 random keys). The three demo documents carry two decoys each. The new category `honeytoken` is on the Policies page and defaults to block.

**Greeklish and look-alike characters (X5).** Before any check the text is cleaned of tricks that keep its length: digits from other scripts (Arabic-Indic, Devanagari, Thai) become 0 to 9, Greek or Cyrillic letters inside a word that mixes scripts or holds a number are folded to the matching Latin ones (a mostly Greek word goes the other way), a capital O or a lower-case l in a long number is read as 0 or 1, and hex, percent-encoded and HTML-entity text is decoded. Names such as "giorgos papadopoulos" are found by Greek surname endings and a list of common surnames, with no model call. `make eval` reports the attacks of these three kinds as one target: 96.2% caught against a target of 80%. A Greek surname with no common ending (for example "Papadaki" in capitals) is still missed.

## Roadmap
Next: (1) browser extension, (2) Slack and Teams, (3) SIEM export, (4) more languages, (5) a small-company edition with login and roles. Details and what is already built: [docs/business/roadmap.md](docs/business/roadmap.md).

## Team
Alexandros, Stelios, Vasilis, Konstantinos.

---
For contributors: start with `docs/TEAM_GUIDE.md` and `CLAUDE.md`.
