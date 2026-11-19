# Sentry

**Every prompt passes the gate.** Sentry (πύλη, "the gate") is one gateway that every AI tool in a company goes through. It finds which AI tools are in use, catches sensitive data before it leaves, even when rewritten, and decides per prompt: **allow, mask, warn, answer with a local model, or block**.

Netcompany Hackathon Athens 2026, Challenge 3: Shadow AI protection and Data Protection.

> Video: [link, added Thu 19 Nov]

## The problem

Companies cannot see which AI tools their people use, and cannot stop a client list, a key or a confidential memo from being pasted into one. Banning the tools does not work: people use them anyway, from personal accounts. Sentry gives them a safe door instead and checks each prompt on the way out. Every decision comes with a reason in plain words and an approved alternative, and the security team sees all of it with the data protected.

## What it does

- **One gateway for every AI tool.** Chat, SDKs, agents, Claude Code and MCP traffic point at one OpenAI-compatible endpoint (LiteLLM). A browser extension covers personal ChatGPT.
- **Detection, cheapest check first.** Text clean-up, checksummed Greek identifiers (AFM, AMKA, IBAN, cards), secret and code rules, people and client names, then confidential-document matching that survives rewording, session memory across prompts, and prompt-injection checks. No paid model is needed.
- **Five outcomes with a reason.** Company Chat shows the outcome in words and an icon. The incident page has a "Why this decision" panel listing the checks that fired.
- **Shadow AI discovery.** The AI tools page lists every tool seen in usage logs as approved, tolerated or unapproved, with the approved alternative. Employees can request a new tool.
- **Policies you can try first.** An editable policy table, shadow mode (record what would happen, change nothing), and a 14-day replay before saving.
- **Security view.** Incidents with sealed identities (a real name needs two people), documents and marked copies that trace a leak to its recipient, teams and roles, impact, a weekly digest, and a compliance report (PDF).
- **Ask a question.** The brief's own question, "Which teams sent client data to unapproved AI tools this week?", is a reviewed query with the SQL shown.
- **Try to break it.** `/break-it` lets anyone attack the checks and see which level caught them.
- **Protects what it inspects.** No raw prompts are stored, and the most sensitive fields use split storage across two separate databases.

## Run it

Requirements: Docker with Compose v2, about 2 GB of free RAM for Docker, and ports 3000, 4000 and 8001 free.

```bash
git clone <this repo>
cd <repo>
cp .env.example .env        # optional: add OPENAI_API_KEY
docker compose up --build
```

Open http://localhost:3000 (app) and http://localhost:8001/docs (API). Without an OpenAI key the offline demo models answer, so everything works. There is no login: get a personal key on the Connect page (`/connect`). The first build downloads the models and takes several minutes. Afterwards the stack is healthy in about 80 seconds and idles at about 1.7 GB.

`make help` lists everything. The ones you need: `make up`, `make down`, `make reset` (fresh database), `make check`, `make eval`, `make e2e`. Walk through the product in [docs/DEMO.md](docs/DEMO.md).

## Architecture

```
 Employee --> web (React) ---------+
 SDKs, agents, Claude Code --------+--> gateway (LiteLLM) --> cloud model | local model
 Browser extension ----------------+        |  checks before and after every call
                                            v
                                        brain (FastAPI) --> Postgres + pgvector, two vaults
```

The gateway fails closed: if the brain is down, nothing passes. Full design, the detection pipeline and the privacy claims: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Results

Measured on 19 Nov 2026 on synthetic data. Method, the full table and the misses: [docs/EVALUATION.md](docs/EVALUATION.md).

| Measure | Result | Target |
| --- | --- | --- |
| Paraphrased document leaks found | 100% (40 of 40); regex baseline 5% | 80% |
| False alarms on clean prompts | 2.1% | 5% |
| Prompts needing no LLM | 100% | 90% |
| Attack sets (2 x 80) | 160 of 160 as expected | |
| Added latency, one request (p95) | 58 ms | under 100 ms |
| Added latency, 3 people at once (p95) | about 260 ms | under 100 ms: **missed** |
| Tests | 912 brain (88% coverage; 37 need the running stack), 114 web, 5 extension | |

## Known limits

- Only traffic through the gateway is stopped. Other tools are seen in usage logs, not blocked.
- Detection is probabilistic. The attack sets pass because failures were fixed after we saw them, so new forms of attack can still pass.
- There is no login in demo mode. Do not expose ports 8001 and 4000 beyond a trusted network.
- The load test misses its latency target with three people at once: the brain is one process.

What Sentry does and does not stop: [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

## Documentation

| Doc | What is in it |
| --- | --- |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Services, request flow, detection pipeline, policy, data model, privacy and split storage |
| [docs/EVALUATION.md](docs/EVALUATION.md) | How accuracy was measured, results, misses |
| [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) | Who we defend against and what we do not stop |
| [docs/DEMO.md](docs/DEMO.md) | The five-minute demo script |
| [docs/GATEWAY_SETUP.md](docs/GATEWAY_SETUP.md) | Pointing a company's AI traffic at the gateway |
| [docs/siem/](docs/siem/README.md) | Sending incidents to a SIEM |
| [docs/business/](docs/business) | Market, competitors, pricing, compliance, roadmap |
| [docs/BRAND.md](docs/BRAND.md) | Name, logo, mascot |

## Roadmap

Built: the browser extension and the SIEM export. Next: Slack and Teams, more languages, and a small-company edition with login and roles. See [docs/business/roadmap.md](docs/business/roadmap.md).

## Team

Alexandros, Stelios, Vasilis, Konstantinos.
