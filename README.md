<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="web/public/brand/sentry-wordmark-reverse.svg">
    <img src="web/public/brand/sentry-wordmark.svg" alt="Sentry" width="300">
  </picture>
</p>

<p align="center"><b>Every prompt passes the gate.</b></p>

Sentry is a gateway that every AI tool in a company goes through. When someone sends a prompt or a file to ChatGPT, Claude, Gemini, an SDK or an agent, Sentry checks it before it leaves. It finds client data, personal IDs, secrets and confidential documents, even when they have been reworded. For each prompt it picks one of five outcomes: **allow, mask, warn, answer with a local model, or block**. People get a reason in plain words and an approved alternative. The security team sees every decision without seeing the data. Sentry also lists which AI tools are in use, including unapproved ones. It runs on your own server, and a single `docker compose up` starts it.

<p align="center">
  <a href="docs/media/sentry-launch.mp4"><img src="docs/media/sentry-launch-poster.jpg" alt="Watch the launch film (1:45)" width="720"></a><br>
  <a href="docs/media/sentry-launch.mp4"><b>▶ Watch the launch film (1:45)</b></a>
</p>

Netcompany Hackathon Athens 2026, Challenge 3: Shadow AI protection and Data Protection.

## Why

Companies can't see which AI tools their people use. They also can't stop a client list, an API key or a confidential memo from being pasted into one. Banning the tools doesn't work, because people switch to personal accounts. Sentry gives people a safe way through instead, so they keep the AI and the company keeps its data.

## How it works

```
 Employee --> web (React) ---------+
 SDKs, agents, Claude Code --------+--> gateway (LiteLLM) --> cloud model | local model
 Browser extension ----------------+        |  checks before and after every call
                                            v
                                        brain (FastAPI) --> Postgres + pgvector, two vaults
```

1. **One endpoint.** Chat, SDKs, agents, Claude Code and MCP traffic all point at one OpenAI-compatible gateway. A browser extension covers personal ChatGPT, Claude and Gemini tabs.
2. **Cheapest check first.** Text clean-up (look-alike letters, Greeklish, encodings), checksummed Greek IDs (AFM, AMKA, IBAN, cards), secret and code rules, then people and client names. After that come confidential-document matching that survives rewording, memory across prompts in a session, and prompt-injection checks. No paid model is needed.
3. **Files too.** PDFs, Word files and images are read, with OCR for scans and images, and go through the same checks. A file stamped RESTRICTED or CONFIDENTIAL is blocked. A file the gate can't read is refused, not passed.
4. **A decision with a reason.** Allow, mask (hide the values and still get an answer), warn (ask first), answer locally (the data never leaves), or block. The incident page shows which checks fired.
5. **Fails closed.** If the brain is down, nothing passes.

## What's in the box

- **Company Chat** with file upload. It shows each outcome with an icon and text.
- **Browser extension** (Chrome, Edge, Brave; MV3). It checks paste, send and file attach on ChatGPT, Claude and Gemini. When a prompt is blocked, it opens Company AI so the person can still get an answer.
- **Shadow AI discovery.** Every tool seen in usage logs is listed as approved, tolerated or unapproved. Employees can request new tools.
- **Policies you can try first.** An editable policy table, shadow mode, and a 14-day replay before you save.
- **Security view.** Incidents with sealed identities (revealing a name takes two people), leak tracing through marked copies, a weekly digest, a compliance PDF and SIEM export.
- **Break it.** At `/break-it` anyone can attack the checks and see which level caught them.
- **Privacy by design.** No raw prompts are stored. The most sensitive fields are split across two separate databases.

## Run it

Requirements: Docker with Compose v2, about 3 GB of free RAM, and ports 3000, 4000 and 8001 free.

```bash
git clone https://github.com/alexkoukos/data-dna.git && cd data-dna
cp .env.example .env        # optional: add OPENAI_API_KEY
docker compose up --build
```

The app runs at http://localhost:3000 and the API at http://localhost:8001/docs. You don't need an OpenAI key: offline demo models answer without one. The first build downloads models and takes a few minutes. After that, the stack is healthy in about 80 seconds. `make help` lists every command. The demo script is in [docs/DEMO.md](docs/DEMO.md).

**Extension:** run `make extension-zip`, open `chrome://extensions`, turn on Developer mode, choose *Load unpacked* and pick `extension/.output/chrome-mv3`. It connects to `localhost:8001` by itself.

## Results

These were measured on 19 Nov 2026 on synthetic data. The method and every miss are in [docs/EVALUATION.md](docs/EVALUATION.md).

| Measure | Result | Target |
| --- | --- | --- |
| Reworded document leaks caught | 100% (40 of 40); regex baseline 5% | 80% |
| False alarms on clean prompts | 2.1% | ≤ 5% |
| Prompts needing no LLM | 100% | 90% |
| Attack sets (2 × 80) | 160 of 160 as expected | |
| Added latency, one request (p95) | 58 ms | < 100 ms |
| Added latency, 3 people at once (p95) | ~260 ms | < 100 ms: **missed** |
| Tests | 912 brain (88% coverage), 114 web, 5 extension | |

## Known limits

- Sentry only stops traffic that goes through the gateway or the extension. Other tools show up in usage logs, but they aren't blocked.
- Detection is probabilistic. The attack sets pass because we fixed the failures we found, so new kinds of attack can still get through.
- Demo mode has no login, so don't expose ports 8001 or 4000 beyond a trusted network.
- The brain runs as one process, which is why latency misses its target under concurrent load.

## Docs

[Architecture](docs/ARCHITECTURE.md) · [Evaluation](docs/EVALUATION.md) · [Threat model](docs/THREAT_MODEL.md) · [Demo](docs/DEMO.md) · [Gateway setup](docs/GATEWAY_SETUP.md) · [SIEM](docs/siem/README.md) · [Business](docs/business) · [Brand](docs/BRAND.md)

## Team

Alexandros, Stelios, Vasilis, Konstantinos.
