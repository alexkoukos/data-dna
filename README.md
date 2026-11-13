# Data DNA

> Video: [link, added Thu 19 Nov]
> An AI gateway that every AI tool in the company goes through: it finds which AI tools are used, catches sensitive data before it leaves (even when rewritten), and decides per prompt: allow, warn, mask, answer with a local model, or block.

Netcompany Hackathon Athens 2026, Challenge 3: Shadow AI protection and Data Protection.

## Concept
_To be written (R1). Source: docs/IDEA_AND_TEAM.md._

## Main features
_To be written (R1)._

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

## Evaluation
_Results from `make eval` (E1)._

## Privacy and governance
_GDPR and EU AI Act (T5)._

## Known limits
_To be written._

## Extra features

**Try to break it (X1).** Open `/break-it`, type anything you think the gateway will miss and press "Check it". The page shows the outcome, the reasons and the eight levels of the pipeline in order, with the ones that found something marked. Nothing typed there is stored and nobody's practice shows up as an incident. A starter button per kind of attack comes from `data/eval/attacks.csv`. `web/e2e/break-it.spec.ts` types ten evasions into the real page and checks each one is stopped.

**Attack file (X2).** `data/eval/attacks.csv` holds 80 invented attacks in 10 kinds (spaced out, encoded, look-alike letters, foreign digits, Greeklish, injection, hidden keys, rewritten documents, decoys, and 8 harmless look-alikes), each with the decision we expect. The expectation is written before looking at the result, so known gaps stay in the file and `make eval` lists them under "Red team" (today: reversed text, base64 injection, a key split by string concatenation, a surname with no common ending, one rewritten salary table). Rows come from `scripts/gen_attacks.py`; to add your own, append rows to the CSV and do not re-run the generator, or add them to the script.

**Decoy credentials (X4).** A confidential document can carry fake keys and mailboxes that exist nowhere else (`honeytokens:` in its header, or `POST /v1/documents/{id}/honeytokens`, which returns lines to paste in). If one appears in a prompt the decision is block, the reason names the document ("that document has left the company"), the incident is linked to it and `audit_log` gets `honeytoken.triggered`. Matching is an exact string compare against random 20 to 40 character values, so ordinary text and look-alike keys never trigger it (tested on 400 random keys). The three demo documents carry two decoys each. The new category `honeytoken` is on the Policies page and defaults to block.

**Greeklish and look-alike characters (X5).** Before any check the text is cleaned of tricks that keep its length: digits from other scripts (Arabic-Indic, Devanagari, Thai) become 0 to 9, Greek or Cyrillic letters inside a word that mixes scripts or holds a number are folded to the matching Latin ones (a mostly Greek word goes the other way), a capital O or a lower-case l in a long number is read as 0 or 1, and hex, percent-encoded and HTML-entity text is decoded. Names such as "giorgos papadopoulos" are found by Greek surname endings and a list of common surnames, with no model call. `make eval` reports the attacks of these three kinds as one target: 96.2% caught against a target of 80%. A Greek surname with no common ending (for example "Papadaki" in capitals) is still missed.

## Roadmap
_From docs/business (T5)._

## Team
Alexandros, Stelios, Vasilis, Konstantinos.

---
For contributors: start with `docs/TEAM_GUIDE.md` and `CLAUDE.md`.
