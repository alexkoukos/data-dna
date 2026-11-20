# TASKS: the board

Status: `[ ]` open, `[~] (name)` in progress, `[x]` done. Claim a task by changing its status in your branch. One person per task. The planning docs these tasks came from (PRD, audit, extra-features list) were removed before submission and are in the git history.
Priority: **P0** must work on 20 Nov, **P1** should, **P2** cut first.

## Foundation
- [x] **S0** Scaffold: locks, tests, CI, devcontainer, Makefile. (Alexandros)
- [x] **S1** P0 `make up` works on a real machine; fix Dockerfiles; CI smoke green. Owner: Alexandros. Done when: fresh clone, `make up`, both URLs load, CI green.
- [~] (Alexandros) **S2** P0 Platform check: Linux, macOS Apple silicon, Windows WSL. Owner: Alexandros. Done when: `make up` works on all three; RAM and first-start time written in README.
- [~] (Stelios) **S4** P0 Gateway inspects the whole request: all conversation turns, system, instructions, prompt, tool definitions; masks in place. Owner: Stelios. Done when: unit + live tests pass, multi-turn p95 < 100 ms.
- [x] **S3** P0 Docker hardening: brain health check start period, brain runs as non-root, nginx pinned, published ports on localhost only. Owner: Stelios. Done when: fresh `make reset && make up` healthy, CI green.
- [x] **S5** P1 Gateway follow-ups after S4: remember acknowledged history per user, tool-description injection warns instead of blocks, drop `organization` instead of refusing, filter and unmask streamed Responses and Anthropic answers, no false block on negated mid-conversation system text. Owner: Stelios. Done when: unit + live tests pass, security review clean.
- [x] **S6** P0 Audit fixes from the 19 Nov audit: fresh-clone start, gateway steering and verdicts, analyst SQL role, CSRF and host checks, size caps, answer and tool-call filtering, MCP proxy, extension fail-closed, infra hygiene, measured README numbers. Owner: Stelios. Done when: `make check`, `make test-gateway` and `make e2e` pass and the PR is merged. Merged in #66.

## Gateway and routing
- [x] **G1** P0 Add LiteLLM gateway service (pin the latest stable image tag from its releases page), per-user virtual keys, custom guardrail calling `brain /v1/inspect`. Owner: Alexandros. Done when: an OpenAI SDK client with a personal key gets a masked-and-answered reply through the gateway; integration test passes.
- [x] **G2** P0 Unmask in answers + output filtering `/v1/inspect-output`. Owner: Alexandros.
- [x] **G3** P0 Warn (409 + ack header) and block (403) responses with reasons and approved alternative. Owner: Alexandros. Block verified by unit test only until D6 can trigger it live.
- [x] **L1** P1 Local model: benchmark llama.cpp vs Ollama, 1B to 4B, Greek quality, on Sat 14; add the winner to compose, never on the critical path. Owner: Stelios.
- [x] **G4** P2 Anthropic-format endpoint (Claude Code demo). Owner: Alexandros.
- [x] **M1** P2 MCP proxy with injection checks on tool results. Owner: Stelios.

## Detection
- [x] **D0** Validators (AFM, AMKA, IBAN, Luhn), normalisation, secrets regex, masking, policy precedence. (scaffold)
- [x] **D1** P0 Presidio + spaCy (en, el) for names, emails, phones; client names via aho-corasick from `clients`. Owner: Stelios.
- [x] **D2** P0 YARA rules for secrets and source code (`rules/*.yar`). Owner: Stelios.
- [x] **D3** P0 Document registry: chunking, MinHash, embeddings (fastembed, ONNX), pgvector search, copy vs paraphrase. Owner: Stelios. **Go/no-go Sat 14**: recall on 20 Greek and English paraphrases.
- [x] **D4** P0 File upload text extraction (PDF, DOCX) into the pipeline. Owner: Stelios.
- [x] **D5** P1 Session memory: rebuild across prompts. Owner: Stelios.
- [x] **D6** P1 Prompt-injection classifier. Owner: Stelios.
- [x] (evaluated, not adopted; merged in #58, see PROGRESS) **D7** P2 LLM judge for borderline scores, cached. Owner: Stelios.
- [x] **P1** P0 Policies from DB + `policies.yaml` seed, editable. Owner: Alexandros.

## Shadow AI, DNA, analyst
- [x] **O1** P0 `scripts/gen_org.py --seed 42` from `data/org/org.yaml`: users, keys, clients, documents, Squid + Zeek logs, incidents. Owner: Stelios.
- [x] **O2** P0 Log ingest + AI tool inventory from `data/ai_tools.csv`. Owner: Stelios.
- [x] **O3** P1 Employee simulator (`scripts/simulate.py`, compose profile `sim`). Owner: Stelios.
- [x] **N1** P1 DNA marks: propose, approve, issue copies, attribution with confidence. Owner: Stelios.
- [x] **N2** P1 Sealed identity + two-person reveal + audit log. Owner: Alexandros.
- [x] **A1** P1 Analyst preset questions with SQL shown. Owner: Alexandros.
- [x] **A2** P2 Free-text analyst questions over read-only views. Owner: Alexandros.

## Web
- [x] **W1** P0 Company Chat: messages, five outcome chips, "Why?" disclosure, warn card, file upload. Owner: Alexandros.
- [x] **W2** P0 Security overview + inventory + incidents list. Owner: Alexandros.
- [x] **W3** P1 Incident detail: puzzle view, timeline, copy attribution, reveal request. Owner: Alexandros.
- [x] **W4** P1 Connect page: URL, personal key, snippets, live status. Owner: Alexandros.
- [x] **W5** P1 Policies and Documents pages. Owner: Alexandros.
- [x] **W6** P0 Responsive at 390 px + axe clean on every route. Owner: Alexandros.

## Evaluation and quality
- [x] **E1** P0 `make eval`: report vs regex baseline, targets pass/fail. Owner: Stelios.
- [x] **E2** P1 promptfoo + garak red team, summary in report. Owner: Stelios.
- [x] **E3** P1 Load test, latency p95. Owner: Stelios.
- [x] **E4** P0 Integration tests through the gateway for all five outcomes. Owner: Alexandros.

## Team data (no code; edit files, then `make validate`)
- [x] **T1** P0 `data/org/org.yaml`: company, 8 teams, 10 clients, AI habits, 14-day storyline. Owners: Konstantinos, Vasilis. Basics Fri 13, storyline Sat 14.
- [x] **T2** P0 3 confidential documents in `data/documents/` (Greek + English). Owner: Konstantinos. Sat 14.
- [x] **T3** P0 `data/eval/prompts.csv`: 60 rows by Sat 14, 200 by Mon 16. Owners: Konstantinos, Vasilis.
- [x] **T4** P0 `data/ai_tools.csv`: about 15 tools rated. Owner: Vasilis. Sun 15.
- [x] **T5** P1 Business pack in `docs/business/`: market, competitors, SWOT, pricing, roadmap, GDPR/AI Act, engagement. Owner: Vasilis. Mon 16 to Wed 18.

## Submission
- [x] **R1** P0 README in the required parts with measured numbers. Owners: Konstantinos (text), Alexandros (setup).
- [x] **R2** P1 Video (YouTube) linked at the top of README. Owner: Konstantinos with Alexandros. Thu 19.
- [ ] **R3** P1 Slides. Owner: Konstantinos. Draft Thu 19, final Tue 24.
- [ ] **R4** P0 Submit Fri 20 by noon, judges have repo access. Owner: Alexandros.

## Extra features
X1 to X32 are recorded in the `PROGRESS.md` entries that name them. Technical items are Alexandros's; business and writing items stay with Vasilis and Konstantinos.
- [x] **SS1** P1 Split storage: two vaults, additive shares, HMAC integrity, tests and demo (branch `task/split-storage`). Done when: `docker compose up` works from a clean clone and `make split-test` passes.
