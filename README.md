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

## Architecture
_Diagram and services table (R1). Source: docs/PRD.md section 7._

## Browser extension

Personal ChatGPT in the browser bypasses the gate, so the extension (`extension/`, Chrome or Edge, Manifest V3, plain JavaScript, no build step) checks paste and send on `chatgpt.com` against the same `POST /v1/inspect` the gate uses, before the text leaves the page.

**Load it (3 clicks)**
1. Open `chrome://extensions`, turn on *Developer mode*, press *Load unpacked* and choose the `extension/` folder.
2. Copy the extension ID shown on its card (or on the Settings page), put it in `.env` as `EXTENSION_ID=...` and run `make up` again. The brain allows browser calls only from `chrome-extension://<that ID>`.
3. Open the extension's Settings, paste your personal key from the **Connect** page and press Save. The gate address defaults to `http://localhost:8001`.

**What it does.** Allow: nothing. Mask: the composer text is replaced with the masked text and a note names the entity types and the "Why?" reasons. Warn: a card with the reasons and *Send anyway*, which is recorded on the incident like the gate's `X-DNA-Ack`. Block and local: the send is stopped and the card offers *Use Company AI*. Every non-allow decision is an incident with the tool "ChatGPT (personal)" and channel `browser`, so the Shadow AI view shows it was intercepted. In shadow mode (X11) nothing is changed or stopped; it is only recorded. The user is the owner of the key, resolved by the brain through the gateway; the extension never sends a user or team. The extension stores only the key, the gate address and a daily counter for its popup, and makes no network calls except to the gate address.

**Limits.** One site (`chatgpt.com`); other sites and the ChatGPT desktop or phone apps are not covered, and a person can disable or remove the extension (the Squid and Zeek logs still see that). Only text is checked: pasted images and file uploads are not. If the gate cannot be reached the extension **fails open**: nothing is blocked, a small "Pyli offline" badge shows, and nothing is recorded. ChatGPT changes its page often, so the composer and send-button selectors in `extension/content.js` may need an update. The test (`web/e2e/extension.spec.ts`) runs against a saved composer page, `extension/test/fixture.html`, not the live site.

## Evaluation
_Results from `make eval` (E1)._

## Privacy and governance
_GDPR and EU AI Act (T5)._

**Break it (X28).** Practice on `/break-it` is never stored and never creates an incident; only counters, a masked preview, the attack kind and an optional nickname (no login, nothing that identifies a person) are kept, in memory. The one exception is the "It got through" button: the person chooses to submit the exact text as a test case, and the button says so. That raw text lives only in a review-queue row until a security user decides. Approve moves it into `data/eval/attacks_scripts.csv` and blanks the row; reject deletes the row at once.

## Known limits
_To be written._

## Extra features

**Try to break it (X1).** Open `/break-it`, type anything you think the gateway will miss and press "Check it". The page shows the outcome, the reasons and the eight levels of the pipeline in order, with the ones that found something marked. Nothing typed there is stored and nobody's practice shows up as an incident. A starter button per kind of attack comes from `data/eval/attacks_scripts.csv`. `web/e2e/break-it.spec.ts` types ten evasions into the real page and checks each one is stopped.

**Attack file (X2).** `data/eval/attacks_scripts.csv` (next to the technique-based `attacks.csv`) holds 80 invented attacks in 10 kinds (spaced out, encoded, look-alike letters, foreign digits, Greeklish, injection, hidden keys, rewritten documents, decoys, and 8 harmless look-alikes), each with the decision we expect. The expectation is written before looking at the result, so known gaps stay in the file and `make eval` lists them under "Script and decoy attacks" (today: reversed text, base64 injection, a key split by string concatenation, a surname with no common ending, one rewritten salary table). Rows come from `scripts/gen_attacks_scripts.py`; to add your own, append rows to the CSV and do not re-run the generator, or add them to the script.

**Decoy credentials (X4).** A confidential document can carry fake keys and mailboxes that exist nowhere else (`honeytokens:` in its header, or `POST /v1/documents/{id}/honeytokens`, which returns lines to paste in). If one appears in a prompt the decision is block, the reason names the document ("that document has left the company"), the incident is linked to it and `audit_log` gets `honeytoken.triggered`. Matching is an exact string compare against random 20 to 40 character values, so ordinary text and look-alike keys never trigger it (tested on 400 random keys). The three demo documents carry two decoys each. The new category `honeytoken` is on the Policies page and defaults to block.

**Greeklish and look-alike characters (X5).** Before any check the text is cleaned of tricks that keep its length: digits from other scripts (Arabic-Indic, Devanagari, Thai) become 0 to 9, Greek or Cyrillic letters inside a word that mixes scripts or holds a number are folded to the matching Latin ones (a mostly Greek word goes the other way), a capital O or a lower-case l in a long number is read as 0 or 1, and hex, percent-encoded and HTML-entity text is decoded. Names such as "giorgos papadopoulos" are found by Greek surname endings and a list of common surnames, with no model call. `make eval` reports the attacks of these three kinds as one target: 96.2% caught against a target of 80%. A Greek surname with no common ending (for example "Papadaki" in capitals) is still missed.

**Break it leaderboard and growing attack set (X28).** `/break-it` also shows today's attempts, how many were stopped, how many got through and the catch rate, plus a top-breakers list by nickname. When an attempt passes but should not have, "It got through" lets the person pick the expected decision (mask, warn or block) and the kind, and sends it to the **Break it review** tab in Security (`/security/review`). Approving appends a row with `source=breakit` and the date to `data/eval/attacks_scripts.csv` (the brain container has that one folder writable); `make eval` then reports those rows on their own line, "Found live, still missed: N", apart from the older attacks. Break it practice still creates no incidents. Tests: `services/brain/tests/test_x28_breakit.py`, `web/src/pages/BreakItBoard.test.tsx`, and `web/e2e/break-it-review.spec.ts` (needs `make up`).

## Roadmap
_From docs/business (T5)._

## Team
Alexandros, Stelios, Vasilis, Konstantinos.

---
For contributors: start with `docs/TEAM_GUIDE.md` and `CLAUDE.md`.
