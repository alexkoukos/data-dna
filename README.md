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

## Roadmap
_From docs/business (T5)._

## Team
Alexandros, Stelios, Vasilis, Konstantinos.

---
For contributors: start with `docs/TEAM_GUIDE.md` and `CLAUDE.md`.
