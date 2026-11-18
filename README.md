# Hive, the gate

> Video: [link, added Thu 19 Nov]

Hive is a browser extension and a dashboard. The extension sits in Chrome, right where people paste into ChatGPT, Claude or Gemini. It checks the text before it is sent, even when the text was rewritten, and decides on the spot: allow, warn, mask, answer with the company's own AI, or block. It always says why. The dashboard shows the security team which AI tools are really used and what was caught.

Netcompany Hackathon Athens 2026, Challenge 3: Shadow AI protection and Data Protection.

## Run it in 3 commands

```bash
git clone https://github.com/alexkoukos/data-dna.git
cd data-dna
docker compose up --build
```

Needs Docker with Compose v2 and free ports 3000 (dashboard), 3100 (demo chat) and 8001 (API). The first start downloads no models: the embedding model is baked into the image. No OpenAI key is needed (see "What an OpenAI key adds").

## Try it in 2 minutes

1. Open the dashboard at http://localhost:3000. It is full of seeded demo data, so every page already has something to look at.
2. Go to **Get the extension** and download `hive-extension.zip`. Unzip it.
3. In Chrome open `chrome://extensions`, turn on Developer mode, choose **Load unpacked** and select the unzipped folder.
4. Open the demo chat at http://localhost:3100. It stands in for ChatGPT, so it works offline.
5. Paste the texts from the [`samples/`](samples/README.md) folder (English in `samples/en`, Greek in `samples/el`, or use the copy buttons on the dashboard's Get the extension page). You will see each outcome:

| Sample | What you see |
| --- | --- |
| `1-allow` | Nothing. The message is sent as written. |
| `2-mask` | A tax number and an IBAN are replaced by `[AFM_1]` and `[IBAN_1]` before sending. The answer shows the real values again, on your page only. |
| `3-warn` | A card: "Check before you send". A client name was found. You can use a safer version, edit, or send anyway and say why. |
| `4-redirect` | A card: "Use the company AI for this". The text matches a confidential document. One click opens the side panel with your question, answered by the company's own model. |
| `5-block` | A card: "This was not sent". It matches the restricted board memo. It says why and what to do instead. |

6. Back in the dashboard, open **Security**: your attempts are incidents now. Names are pseudonyms, and a real name needs a reason and a second person.
7. Optional: pair the extension to a demo person (dashboard, Get the extension, step 3) so incidents carry that person's team. Run `make simulate` to make the dashboard move.

## Concept

Banning AI at work does not work: people use their personal accounts instead, and the company loses sight of it. Tools that match patterns miss data that was rewritten. Hive takes a third way. It sits in the browser, where the paste happens, understands what is confidential, and lets people keep working: it masks, redirects or explains instead of just saying no.

Two sources feed one inventory of AI tools. The extension reports which AI sites people visit (the site and the time, never the page). Network logs (Squid and Zeek) catch AI use from browsers without the extension, desktop apps and scripts.

## Main features

What Challenge 3 asks for, and where to see it:

| Ask | Where |
| --- | --- |
| Discover which AI tools are in use, approved or not | Dashboard, Security, AI tools: every tool with risk rating, teams, trend, the approved alternative, and whether it was seen by the extension, the network logs or both. The extension also shows a banner on an unapproved tool. |
| Detect sensitive data before it reaches an AI service | The extension checks in the browser first (L1, under a millisecond), then on the company server (L2). |
| Enforce a policy: allow, redact, warn or block | Five outcomes, per data category and per document, editable in Security, Policies, with the last 14 days replayed before you save. Team and role exceptions on Teams and roles. |
| Analysts ask "Which teams sent client data to unapproved AI tools?" | Security, Ask: five preset questions, each showing the answer table and the read-only SQL behind it. Free text works when a model is available. |
| Inspectable inventory with risk ratings, configurable policy | AI tools and Policies pages. |
| Working prototype ingesting logs and prompts | Squid and Zeek logs are read at start and through `POST /v1/logs/ingest`. Prompts arrive through `POST /v1/check`. |
| Live demo: detected, acted on, explained | The five samples above. Every card says what happened, why, and what to do instead. |
| Bonus: prompt injection | Pasted instructions aimed at the AI (including hidden, encoded and Greeklish ones) are blocked. |

How the check works, cheapest first:

- **L1, in the browser, no network.** Cleans the text (invisible characters, digits from other scripts, spaced-out digits, base64 and hex), then finds Greek tax numbers (AFM), social security numbers (AMKA), IBANs and payment cards by checksum, plus API keys, Greek phone numbers, emails, client names from the company's list, and source code. The rules are in one file, [`shared/rules.json`](shared/rules.json), and both the browser and the server test against the same fixtures, so they cannot drift apart.
- **L2, on the company server.** Compares the text with registered confidential documents (copies, light edits and full paraphrases in Greek and English), remembers what one person sent across prompts (so a document rebuilt from three pieces is caught), looks for prompt injection, and applies the policy for that person's team. No language model is needed for any of this.
- **If the server is down.** The extension still runs L1 and tells the person the server was not reached. Decisions made offline are sent later and become incidents.

Also built: decoy credentials hidden in documents, sealed identities with a two-person reveal and an audit log, per-copy marks that name which copy of a document leaked (Data DNA), shadow mode, a compliance report, ROI numbers and weekly summaries.

### More features (see `docs/EXTRA_FEATURES.md`)
- **Why this decision (X23).** Every decision carries a short list of the checks that fired (patterns, rules, injection phrases, people and contact model, client list, document matching with its score, session memory, the policy). It is stored on the incident and shown on the incident page. It holds only entity names and masked previews, never the prompt.
- **Shadow mode (X11).** On the Policies page, one switch lets every message through while the dashboard records what the policy would have done ("would have blocked 12"). Use it for the first weeks in a company. The setting is stored in the database and every change is audited.
- **Compliance report (X17).** The Policies page has a PDF button (`GET /v1/compliance-report.pdf`). It maps what the gateway does to GDPR, NIS2 and the EU AI Act with the live numbers behind each line. It supports a company's own review; it is not legal advice. The same table is in `docs/business/compliance-mapping.md`.
- **Attack set (X2).** `data/eval/attacks.csv` holds 80 red-team prompts (invisible characters, look-alike letters, hex, URL, ROT13, reversed, spaced, leetspeak, prompt injection, document rewrites, secrets, combined tricks, and normal prompts that must not be flagged). `make eval` reports how many are handled and lists the misses honestly: 77 of 80 today.
- **More Greek identifiers (X6).** Police ID (ADT), number plates, Greek mobile and landline numbers (with or without +30), and, next to their names, passport and GEMI numbers are found and masked. They have no checksum, so a few look-alikes such as "TAX 1234" can match a plate shape; the cost is one needless mask.
- **Answer check (X7).** What a model says is checked before the person sees it: echoed secrets and identifiers are masked (patterns and YARA rules), and an answer that reproduces a protected document is withheld whole.
- **Try a policy first (X12).** On the Policies page, "Try on the last 14 days" shows how many past incidents a change would have made stricter or looser, before you save. It replays the stored categories and matched document, so no raw prompt is ever kept.

## Setup and run

Requirements: Docker with Compose v2. Free ports: 3000, 3100, 8001.

```bash
docker compose up --build        # everything the judges need
```

| Service | Port | What it is |
| --- | --- | --- |
| `web` | 3000 | The dashboard (React). Also serves `/extension.zip` and the sample texts. |
| `mock-ai` | 3100 | A tiny ChatGPT-like page for the offline demo and the tests. |
| `brain` | 8001 | The API (FastAPI): checks, policy, incidents, inventory, analyst questions. Docs at /docs. |
| `db` | internal | Postgres with pgvector (official image plus the extension). |

Optional, never needed for the demo:

| Command | What it adds |
| --- | --- |
| `make local` | A local model (Ollama) so "Ask the company AI" gives real answers. Without it the answer is a clearly labelled stand-in. First start downloads about 1 GB. |
| `make gateway` | A LiteLLM gateway on port 4000 (see "Other ways in"). |
| `make simulate` | Simulated employees use AI sites, so the dashboard moves while you demo. |

**What an OpenAI key adds.** Put `OPENAI_API_KEY` in `.env`. It only turns on free-text analyst questions through a hosted model and nothing else. Everything in "Try it in 2 minutes" works without it.

**Build the extension yourself.** `make extension` builds it into `extension/.output/chrome-mv3`. Load that folder unpacked.

Measured on Windows 11 with WSL 2 (Ubuntu 24.04, Docker Desktop, 16 CPUs, 15.6 GB), fresh clone, no build cache, 17 Nov 2026:

| What | Result |
| --- | --- |
| Build from scratch (`docker compose build --no-cache`) | 113 s |
| Start until all four services are healthy (images built, empty database, demo data seeded) | 31 s |
| RAM when idle | about 770 MB: brain 682 (it holds the embedding and language models), database 57, demo chat 15, dashboard 15 |
| Image sizes | brain 2.5 GB, database 741 MB, demo chat 239 MB, dashboard 95 MB |

On the same machine every Playwright test passes against this stack: 20 of 21 extension tests (the 21st only runs when the server is stopped) and 40 of 41 dashboard tests (the skipped one needs the optional gateway). Before the pivot, on macOS Apple silicon (OrbStack), a build took 72 s and a start 48 s with the gateway running. Native Linux and macOS arm64 runs of the new stack are still to be done.

## Architecture

```
┌──────────────────────────── Chrome ────────────────────────────┐
│ Content script on AI sites ─► Service worker (MV3)             │
│  intercepts paste and send     policy cache, queue, L2 client  │
│  shows the card, masks,        L1 runs in the content script   │
│  restores values in answers                                    │
│ Popup · Side panel (company AI) · Settings                     │
└───────────────────────────────┬────────────────────────────────┘
                                │ HTTPS or HTTP, JSON, device token
┌───────────────────────────────▼────────────────────────────────┐
│ brain (FastAPI)                                                │
│  /v1/check  /v1/events  /v1/policy  /v1/ask-local  /v1/pair    │
│  /v1/inventory  /v1/incidents  /v1/ask  /v1/logs/ingest        │
│  detection · documents · policy · sessions · incidents         │
├───────────────┬──────────────────────┬─────────────────────────┤
│ Postgres +    │ embeddings (ONNX,    │ log ingest              │
│ pgvector      │ multilingual, CPU)   │ (Squid, Zeek)           │
└───────────────┴──────────────────────┴─────────────────────────┘
        ▲                                   ▲
 web (dashboard + /extension.zip)     Ollama (optional, "company AI")
 mock-ai (demo chat)                  LiteLLM gateway (optional)
```

- `extension/` WXT, TypeScript strict, React for the popup, side panel and settings. Every DOM selector lives in one adapter per site (`src/adapters/`).
- `services/brain/` Python 3.12, FastAPI, SQLAlchemy 2.
- `web/` React, Vite, Tailwind v4.
- `shared/` the L1 rules and test fixtures used by both sides.
- `data/` all synthetic: a 200-person company, 10 clients, 3 confidential documents, 14 days of logs and a storyline hidden in them.
- Design notes: [docs/PRD.md](docs/PRD.md) (original design), [docs/PIVOT.md](docs/PIVOT.md) (what changed and why).

## Evaluation

`make eval` compares Hive with a regex-and-keyword baseline on 195 labelled prompts and 160 attack prompts, and writes `eval/report.md`. Targets were fixed before building. Run on 17 Nov 2026:

| Metric | Target | Result |
| --- | --- | --- |
| Recall on paraphrased document leaks | at least 80% | 92.5% (baseline 5.0%) |
| False alarms on clean prompts | at most 5% | 2.1% |
| Added latency, p95, no language model | under 100 ms | 23.7 ms |
| Prompts using zero language-model tokens | at least 90% | 100% |
| Greeklish, look-alike and foreign-digit attacks caught | at least 80% | 96.2% |
| Decoy credentials raise the alarm | 100% | 100% |

By leak type, recall is 100% for copies, light edits, patterns and split-across-prompts leaks, and 92.5% for paraphrases (baseline 0% to 74%). Greek prompts have 5.6% false alarms (n=18), English 0.0% (n=30). Where we miss, the report lists the exact prompts: for example, an English rewrite of the salary bands, a surname with no common Greek ending, and a key split by string concatenation.

Extension, measured on 17 Nov 2026 on a laptop:

- L1 in the browser: p50 0.02 ms, p95 0.03 ms on typical prompts (target: under 5 ms).
- `/v1/check` on the server including document matching: about 20 to 50 ms.
- 34 unit tests in the browser engine and 27 shared fixtures that the brain also passes.
- 21 end-to-end tests in a real Chromium with the extension loaded: all five outcomes in English and Greek, masking and restoring, the offline path, and an accessibility check (axe) of the popup, side panel and settings.
- Brain: 381 tests, 91% coverage. Dashboard: 76 tests.

## Privacy and governance

- **What is checked.** The text you paste or send in an AI chat, first in your browser, then on your company's own server. It goes nowhere else.
- **What is kept.** An incident only when something was found: the kind of data, a masked preview such as `GR••••0695`, the decision and the reason. Never the full message and never the real values. Messages that match nothing are not stored. In a real deployment (demo mode off) records are deleted after 30 days; the period is configurable.
- **What the extension reports.** Which AI sites you visit (site and time). No page content, no prompt text.
- **Names.** The dashboard shows pseudonyms. A real name needs a written reason and a second approver, and every look is in the audit log.
- **Transparency.** The extension's settings page explains all of this in plain words, as the EU AI Act and GDPR ask.
- **Real data.** None. Everything in this repository is invented.
- More: [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md), `GET /v1/compliance-report.pdf`, [docs/business/compliance-mapping.md](docs/business/compliance-mapping.md).

Why the extension asks for each permission:

| Permission | Why |
| --- | --- |
| `storage` | Remember the policy, settings and today's counters on this device. |
| `alarms` | Refresh the policy every minute and send queued events. |
| `sidePanel` | Show the company AI next to the page. |
| Access to chatgpt.com, claude.ai, gemini.google.com and localhost | Read the message box and the send button on those sites, and talk to the company server. Nothing else is read. |

## Known limits

- Only Chrome is supported. There is no Firefox build.
- The ChatGPT, Claude and Gemini adapters are written from the sites' current page structure and have only been tested on the demo chat. A site redesign breaks one adapter (one file) and nothing else. Other AI sites get the telemetry and the unapproved-tool banner but no text check.
- A person can leave the extension off, use another browser or a personal device. The network logs catch the visit but not the text.
- The stack was run and timed on Windows with WSL 2 only. Native Linux and macOS arm64 runs of the new stack have not been made yet (the arm64 image build runs in CI).
- Paraphrase detection is 92.5%, not 100%. Short Greek business text can wrongly match a long contract (for example a payment reminder that resembles the Delphi agreement). The risk is a needless "use the company AI" card.
- Free-text analyst questions need a model (OpenAI key or `make local`). The five presets always work.
- Fail mode is fixed: if the server is unreachable, everything the browser's own checks find is still applied and the rest is let through and logged. It is not yet editable per category in the dashboard.
- Single company, single server. No sign-in: identity is a pairing code in the demo and a Chrome policy in production ([deploy/](deploy/README.md)).

## Other ways in

The earlier design put a LiteLLM gateway in front of AI APIs. It still works and is not part of the demo: `make gateway` starts it on port 4000, and [docs/GATEWAY_SETUP.md](docs/GATEWAY_SETUP.md) shows how to point scripts and coding tools at it. It covers what a browser extension cannot: command-line tools and code.

## Extra features

**Try to break it (X1).** Open `/break-it`, type anything you think the gateway will miss and press "Check it". The page shows the outcome, the reasons and the eight levels of the pipeline in order, with the ones that found something marked. Nothing typed there is stored and nobody's practice shows up as an incident. A starter button per kind of attack comes from `data/eval/attacks_scripts.csv`. `web/e2e/break-it.spec.ts` types ten evasions into the real page and checks each one is stopped.

**Attack file (X2).** `data/eval/attacks_scripts.csv` (next to the technique-based `attacks.csv`) holds 80 invented attacks in 10 kinds (spaced out, encoded, look-alike letters, foreign digits, Greeklish, injection, hidden keys, rewritten documents, decoys, and 8 harmless look-alikes), each with the decision we expect. The expectation is written before looking at the result, so known gaps stay in the file and `make eval` lists them under "Script and decoy attacks" (today: reversed text, base64 injection, a key split by string concatenation, a surname with no common ending, one rewritten salary table). Rows come from `scripts/gen_attacks_scripts.py`; to add your own, append rows to the CSV and do not re-run the generator, or add them to the script.

**Decoy credentials (X4).** A confidential document can carry fake keys and mailboxes that exist nowhere else (`honeytokens:` in its header, or `POST /v1/documents/{id}/honeytokens`, which returns lines to paste in). If one appears in a prompt the decision is block, the reason names the document ("that document has left the company"), the incident is linked to it and `audit_log` gets `honeytoken.triggered`. Matching is an exact string compare against random 20 to 40 character values, so ordinary text and look-alike keys never trigger it (tested on 400 random keys). The three demo documents carry two decoys each. The new category `honeytoken` is on the Policies page and defaults to block.

**Greeklish and look-alike characters (X5).** Before any check the text is cleaned of tricks that keep its length: digits from other scripts (Arabic-Indic, Devanagari, Thai) become 0 to 9, Greek or Cyrillic letters inside a word that mixes scripts or holds a number are folded to the matching Latin ones (a mostly Greek word goes the other way), a capital O or a lower-case l in a long number is read as 0 or 1, and hex, percent-encoded and HTML-entity text is decoded. Names such as "giorgos papadopoulos" are found by Greek surname endings and a list of common surnames, with no model call. `make eval` reports the attacks of these three kinds as one target: 96.2% caught against a target of 80%. A Greek surname with no common ending (for example "Papadaki" in capitals) is still missed.

## Roadmap

Next: the Firefox build, per-category fail modes in the policy editor, a policy for copy and paste of whole files, and Chrome Web Store publishing. Longer term: desktop apps through an endpoint agent, and single sign-on. Market, pricing and the engagement model are in [docs/business](docs/business).

## Team

Alexandros, Stelios, Vasilis, Konstantinos.

---
For contributors: start with `docs/TEAM_GUIDE.md` and `CLAUDE.md`.
