<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/media/sentry-logo-dark.png">
    <img src="docs/media/sentry-logo.png" alt="Sentry" width="320">
  </picture>
</p>

<p align="center"><b>Every prompt passes the gate.</b></p>

Sentry is a gateway that every AI tool in a company goes through. When someone sends a prompt or a file to ChatGPT, Claude, Gemini, an SDK or an agent, Sentry checks it before it leaves. It finds client data, personal IDs, secrets and confidential documents, even when they have been reworded. For each prompt it picks one of five outcomes: **allow, mask, warn, answer with a local model, or block**. People get a reason in plain words and an approved alternative. The security team sees every decision without seeing the data. Sentry also lists which AI tools are in use, including unapproved ones. For the borderline cases we fine-tuned our own small local model, **dna-judge** (Gemma 3 1B + LoRA). On held-out data it cut false alarms from 36 of 60 to 1 of 60. Sentry runs on your own server, and a single `docker compose up` starts it.

<p align="center">
  <a href="https://www.youtube.com/watch?v=oqroMNMVXQg"><img src="docs/media/sentry-launch-thumb.jpg" alt="Watch the Sentry launch film on YouTube" width="720"></a><br>
  <a href="https://www.youtube.com/watch?v=oqroMNMVXQg"><b>▶ Watch the launch film on YouTube (1:45)</b></a>
</p>

<p align="center"><b>Presentation:</b> <a href="docs/sentry-pitch.pptx">Sentry pitch deck</a> (PowerPoint, 17 slides, in Greek)</p>


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
3. **Our own fine-tuned judge.** For matches that are too close to call, we trained **dna-judge**, a LoRA fine-tune of Gemma 3 1B on 1,643 invented examples (44% Greek). It runs locally on Ollama and answers YES or NO with a reason in JSON. Details are under [Fine-tuned model](#fine-tuned-model).
4. **Files too.** PDFs, Word files and images are read, with OCR for scans and images, and go through the same checks. A file stamped RESTRICTED or CONFIDENTIAL is blocked. A file the gate can't read is refused, not passed.
5. **A decision with a reason.** Allow, mask (hide the values and still get an answer), warn (ask first), answer locally (the data never leaves), or block. The incident page shows which checks fired.
6. **Fails closed.** If the brain is down, nothing passes.

## What's in the box

- **Company Chat** with file upload and pictures the model can see. It shows each outcome with an icon and text. Every picture is read the way a model would see it first: text a person can't see (near-white, low contrast, under transparency), rotated text, QR codes and metadata are all checked, and hidden text or an injection blocks the message. Handwriting is read too, orders to the AI written inside a file ask first, data hidden inside an image file (steganography) is blocked, and models only ever get a redrawn copy of a picture.
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

The app runs at http://localhost:3000 and the API at http://localhost:8001/docs. You don't need an OpenAI key: offline demo models answer without one. The first build downloads models and takes a few minutes. After that, the stack is healthy in about 80 seconds. Every command is listed under [Commands](#commands). The demo script is in [docs/DEMO.md](docs/DEMO.md).

**Extension:** run `make extension-zip`, open `chrome://extensions`, turn on Developer mode, choose *Load unpacked* and pick `extension/.output/chrome-mv3`. It connects to `localhost:8001` by itself.

## Commands

`make help` prints this list. Commands marked *stack* need `make up` first.

| Command | What it does |
| --- | --- |
| `make doctor` | Checks that Docker, Compose, git, uv, Node and npm are installed and that `.env` exists. |
| `make setup` | First time only: creates `.env` from `.env.example` and installs the brain and web dependencies exactly as locked. |
| `make up` | Builds and starts the whole stack and waits until it is healthy (the judges' command). |
| `make down` | Stops the stack. |
| `make logs` | Follows the logs of every service. |
| `make reset` | Stops the stack and deletes the local synthetic database, so the next `make up` seeds it fresh. |
| `make check` | Everything CI checks: `validate`, `lint`, `typecheck` and `test`. Run it before every commit. |
| `make validate` | Checks the team's data files (prompts, AI tools, org). |
| `make lint` | Runs ruff and the web linter and formatter in check mode. |
| `make typecheck` | Runs mypy on the brain and builds the web app with TypeScript. |
| `make test` | Unit tests for the brain, the web app and the extension. |
| `make test-extension` | Extension unit tests only. |
| `make fmt` | Formats the brain and web code. |
| `make e2e` | *stack*: browser end-to-end and accessibility tests (Playwright). |
| `make test-gateway` | *stack*: integration tests through the gateway. |
| `make eval` | Detection report against the regex baseline and the targets; writes `eval/report.md`. |
| `make calibrate` | Sweeps the paraphrase cutoff; writes `docs/calibration.md` and `docs/calibration.svg`. |
| `make redteam` | *stack*: attacks the checks with promptfoo cases and garak's known attack prompts. |
| `make loadtest` | *stack*: measures latency under concurrent load. |
| `make simulate` | *stack*: simulated employees chat through the gateway so the dashboard fills up. |
| `make local` | Starts the optional local model (Ollama, gemma3:1b; the first start downloads about 1 GB). |
| `make injection-model` | Downloads the optional prompt-injection classifier (about 740 MB) for the brain. |
| `make split-demo` | Split storage demo: seeds salaries, dumps one vault, adds values up, tampers with a share. |
| `make split-test` | Split storage tests inside the containers. |
| `make siem` | Starts the demo syslog receiver and follows incoming incidents (set `SIEM_SYSLOG_HOST=syslog-receiver` in `.env` first). |
| `make extension-zip` | Builds the browser extension and packs it as `sentry-extension.zip`. |
| `make judge-data` | Regenerates the dna-judge fine-tune data from `data/train_org`. |
| `make judge-ollama` | Starts a separate Ollama for the judge on port 11435. |
| `make judge-eval` | Compares plain gemma3:1b with dna-judge on the test set (needs `make judge-ollama` and the dna-judge model). |

## Results

Measured on synthetic data. The method and the commands to reproduce each number are in [docs/EVALUATION.md](docs/EVALUATION.md).

| Measure | Result | Target |
| --- | --- | --- |
| Reworded document leaks caught | 100% (40 of 40); regex baseline 5% | 80% |
| False alarms on clean prompts | 2.1% | ≤ 5% |
| Prompts needing no LLM | 100% | 90% |
| Fine-tuned judge (dna-judge): false alarms on 60 hard harmless prompts | 1 of 60 (plain Gemma: 36) | ≤ 5 |
| Attack sets (2 × 80) | 160 of 160 as expected | |
| Added latency, one request (p95) | 58 ms | < 100 ms |
| Tests | 1,154 brain (89% coverage), 148 web, 49 extension | |

## Fine-tuned model

**dna-judge** is our own model, a LoRA fine-tune of Gemma 3 1B. It answers one question: does this prompt really leak this document or client? It runs on your own server through Ollama, so no data leaves.

- **Training:** 1,643 training and 289 validation examples from an invented company, 30% leaks and 44% Greek. We trained on a Kaggle T4, merged the adapter and converted it to GGUF.
- **Test:** 639 rows from two other invented companies that the model never saw during training.

| | Plain Gemma 3 1B | **dna-judge** |
| --- | --- | --- |
| False alarms on the 60 hard harmless prompts | 36 | **1** |
| Precision at 30% leaks | 35% | **92%** |
| Recall | 94% | 91% |
| Valid JSON with a reason | 0% | **100%** |

To reproduce it, follow [docs/experiments/judge-finetune.md](docs/experiments/judge-finetune.md) (data in `data/finetune/`, training in `scripts/train_judge_lora.py`) and run `make judge-eval`. The judge is evaluated but not called in the live pipeline: the brain decides without a model call.

## The business

**Employees keep their AI, the company keeps its data.** Prices, the plan and the customer numbers below are assumptions to be checked in pilots. No customer has been interviewed yet. Sources and the full analysis are in [docs/business](docs/business).

**The problem.** 77% of employees who use generative AI paste data into prompts, and 82% of those pastes come from personal accounts (LayerX 2025). Shadow AI adds about USD 670,000 to the average cost of a breach, and 63% of organisations have no AI governance policy (IBM 2025). NIS2, DORA and GDPR ask the CISO for proof of control, not a policy PDF. AI-literacy duties under the AI Act (Article 4) already apply.

**Who pays.** Greek companies with 50 to 1,000 staff that hold confidential client data: consultancies and IT integrators, law firms, banks, insurers and healthcare. The CISO buys and the DPO approves. The employee matters just as much: if Sentry gets in their way, they go back to personal ChatGPT. That is why it answers safely instead of blocking. System integrators are both customers and a sales channel.

**Market.** About EUR 18M a year in Greece and EUR 1.1B in the EU (bottom-up: firms with 50+ staff in target sectors, at EUR 9 per office user per month). Gartner puts securing AI at about USD 4.8B worldwide in 2027. Large companies are buying their way in: SentinelOne bought Prompt Security, Check Point bought Lakera and Akamai bought LayerX. Greece is early, with 8.93% of businesses using AI against 20% across the EU.

**What sets it apart.** Each part exists somewhere else on its own. No product we found combines them where the data leaves:

| | Purview | LayerX / Harmonic | NordLayer | Prompt Security | EchoMark | **Sentry** |
| --- | --- | --- | --- | --- | --- | --- |
| Shadow AI discovery | ✓ | ✓ | ✓ | ✓ | – | ✓ |
| Mask PII and secrets (Greek IDs with checksums) | ✓ | ✓ | ✓ | ✓ | – | ✓ |
| Catch a **reworded** confidential document | – | ~ | – | – | – | ✓ |
| Add up pieces **across several prompts** | – | – | – | – | – | ✓ |
| **Answer locally** instead of blocking | – | – | – | – | – | ✓ |
| Trace **which copy** leaked | – | – | – | – | ✓ | ✓ |

Based on public product pages. "–" means we found no documentation for it, and "~" means partial coverage.

**Pricing (proposal).** *Discover* EUR 3 per user per month (shadow AI discovery and reports). *Protect* EUR 9 (adds the gateway, extension, Company AI, masking and the local model). *Enterprise* is quoted per customer (adds traced copies, SIEM, on-prem and SSO). Annual contracts, with a minimum of 50 users. With tokens passed through at cost, AI for everyone works out at about USD 14 per user per month. ChatGPT Business costs USD 20 and doesn't check any of the data.

**How we sell it.** First, 2 weeks in shadow mode on the customer's own traffic, where the dashboard shows "we would have stopped 12". Then a 30-day pilot in one team, then an annual contract and expansion. For a 200-person consultancy with NDA penalties averaging EUR 675k, the subscription pays for itself if the yearly chance of a client-data leak is above **3.2%**.

**Plan.** These figures come from a financial model built on stated assumptions.

| | 2027 | 2028 | 2029 |
| --- | --- | --- | --- |
| Customers | 8 | 28 | 69 |
| ARR | EUR 145k | EUR 553k | EUR 1.42M |
| Gross margin | 66% | 74% | 75% |

Break-even comes at around 70 customers, in early 2030. Each customer pays back its acquisition cost in 12.3 months, and LTV/CAC is 4.9×. We plan a EUR 450k pre-seed (Feb 2027), then a EUR 1.2M seed (Sep 2028) only if we reach 20 customers, NRR of at least 100% and payback under 18 months. The critical path to the first paid contracts runs through design partners and funding, not code. That is why we raise in parallel with the pilots.

**Top risks.** (1) Large vendors bundle this "for free". We answer by focusing on Greek, mid-size firms and integrations. (2) False alarms drive employees away. Shadow mode comes first, the thresholds are tunable, and we warn before we block. (3) Security sales cycles are slow. Shadow mode, integrators and the compliance report help shorten them. (4) A breach of our own system. We store no prompts, and login, a pen test and cyber insurance come before any pilot.

## Known limits

- Sentry only stops traffic that goes through the gateway or the extension. Other tools show up in usage logs, but they aren't blocked.
- Detection is probabilistic, so new kinds of attack can still get through. Shadow mode measures this on real traffic before anything is enforced.
- Demo mode has no login, so don't expose ports 8001 or 4000 beyond a trusted network.

## Docs

[Pitch deck](docs/sentry-pitch.pptx) · [Architecture](docs/ARCHITECTURE.md) · [Evaluation](docs/EVALUATION.md) · [Fine-tuned model](docs/experiments/judge-finetune.md) · [Threat model](docs/THREAT_MODEL.md) · [Demo](docs/DEMO.md) · [Gateway setup](docs/GATEWAY_SETUP.md) · [SIEM](docs/siem/README.md) · [Business](docs/business) · [Brand](docs/BRAND.md)

## Team

Alexandros, Stelios, Vasilis, Konstantinos.
