# Sentry

**Every prompt passes the gate.** Sentry (πύλη, "the gate") is one gateway that every AI tool in a company goes through. It finds which AI tools are in use, catches sensitive data before it leaves, even when rewritten, and decides per prompt: **allow, mask, warn, answer with a local model, or block**.

Netcompany Hackathon Athens 2026, Challenge 3: Shadow AI protection and Data Protection.

> Video: [link, added Thu 19 Nov]

## The problem

Companies cannot see which AI tools their people use, and cannot stop a client list, a key or a confidential memo from being pasted into one. Banning the tools does not work: people use them anyway, from personal accounts. Sentry gives them a safe door instead and checks each prompt on the way out. Every decision comes with a reason in plain words and an approved alternative, and the security team sees all of it with the data protected.

## What it does

- **One gateway for every AI tool.** Chat, SDKs, agents, Claude Code and MCP traffic point at one OpenAI-compatible endpoint (LiteLLM). A browser extension covers personal ChatGPT.
- **Files through the gateway are read too.** A PDF, Word file or image sent straight to the gateway by a script or agent is read (with OCR) and checked; a stamped file is blocked, and a file the gate cannot read is refused instead of passed.
- **Detection, cheapest check first.** Text clean-up, checksummed Greek identifiers (AFM, AMKA, IBAN, cards), secret and code rules, people and client names, then confidential-document matching that survives rewording, session memory across prompts, and prompt-injection checks. No paid model is needed.
- **Five outcomes with a reason.** Company Chat shows the outcome in words and an icon. The incident page has a "Why this decision" panel listing the checks that fired.
- **File upload in Company Chat.** Attach or drop up to 3 PDF, Word, text, Markdown, CSV or image files. The brain reads them (checked by content, size, page and time limits, OCR for images and scanned PDFs, nothing stored) and the text goes through the same checks as a typed prompt, so the five outcomes apply to files too. When the extension stops an upload on ChatGPT it opens Company Chat, which offers to take the file instead.
- **Shadow AI discovery.** The AI tools page lists every tool seen in usage logs as approved, tolerated or unapproved, with the approved alternative. Employees can request a new tool.
- **Policies you can try first.** An editable policy table, shadow mode (record what would happen, change nothing), and a 14-day replay before saving.
- **Security view.** Incidents with sealed identities (a real name needs two people), documents and marked copies that trace a leak to its recipient, teams and roles, impact, a weekly digest, and a compliance report (PDF).
- **Ask a question.** The brief's own question, "Which teams sent client data to unapproved AI tools this week?", is a reviewed query with the SQL shown.
- **Try to break it.** `/break-it` lets anyone attack the checks and see which level caught them.
- **Protects what it inspects.** No raw prompts are stored, and the most sensitive fields use split storage across two separate databases.

## Run it

Requirements: Docker with Compose v2, about 3 GB of free RAM for Docker, and ports 3000, 4000 and 8001 free.

```bash
git clone <this repo>
cd <repo>
cp .env.example .env        # optional: add OPENAI_API_KEY
docker compose up --build
```

Open http://localhost:3000 (app) and http://localhost:8001/docs (API). Without an OpenAI key the offline demo models answer, so everything works. There is no login: get a personal key on the Connect page (`/connect`). The first build downloads the models and takes several minutes. Afterwards the stack is healthy in about 80 seconds and idles at about 1.9 GB (the AI gateway, which Company Chat answers through, is about 0.75 GB of that).

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

## Browser extension

The extension (`extension/`, Chrome, Edge or Brave, Manifest V3, WXT + React + TypeScript) checks paste, send and file attach on ChatGPT, Claude and Gemini against the gate before anything leaves the page.

**Build and load it**
```bash
make extension-zip          # builds extension/.output/chrome-mv3 and sentry-extension.zip
```
1. Open `chrome://extensions`, turn on *Developer mode*, press *Load unpacked* and choose `extension/.output/chrome-mv3` (or unzip `sentry-extension.zip` and choose that folder).
2. That is all. On install the extension connects to `http://localhost:8001` by itself, picks the first demo person, and switches on in AI tabs that are already open. The popup says *Connected as …*. If the server is not up yet it says so and offers *Connect*. To act as someone else, use Settings (a pairing code from the dashboard, or pick a demo user); the address must be https, or http on localhost.
3. With `make up` running, paste a prompt holding an IBAN on any of the three sites.

**What it does.** Allow: sent as written. Mask: the composer text is replaced and the real values come back in the answer, on that page only. Warn: a card asks first. Block and local: the send is stopped and the card points to Company AI (side panel, or a tab if the browser has no side panel). A file stamped RESTRICTED or CONFIDENTIAL is blocked. If the server cannot be reached the browser's own checks still run; if the server refuses to read the text (too long, malformed) it fails closed.

**Hardening.** The server address must be https (or localhost); the token is never readable by a page script; only the AI sites' content scripts may message the worker; page URLs are sent without query or fragment; text over 100,000 characters and files over about 20 MB are refused; extension pages run under a strict content security policy.

**Tests.** `cd extension && npm test` (unit), `npm run e2e` (real Chromium with the built extension against the mock AI page, incl. axe accessibility; needs `make up`).

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
| [docs/business/](docs/business) | Market, competitors, pricing, compliance |
| [docs/BRAND.md](docs/BRAND.md) | Name, logo, mascot |

## Team

Alexandros, Stelios, Vasilis, Konstantinos.
