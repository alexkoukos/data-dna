# TASKS: the board

Status: `[ ]` open, `[~] (name)` in progress, `[x]` done. Claim a task by changing its status in your branch. One person per task. Section numbers point to `docs/PRD.md`.
Priority: **P0** must work on 20 Nov, **P1** should, **P2** cut first.

## Foundation
- [x] **S0** Scaffold: locks, tests, CI, devcontainer, Makefile. (Alexandros)
- [x] **S1** P0 `make up` works on a real machine; fix Dockerfiles; CI smoke green. Owner: Alexandros. Done when: fresh clone, `make up`, both URLs load, CI green.
- [~] (Alexandros) **S2** P0 Platform check: Linux, macOS Apple silicon, Windows WSL. Owner: Alexandros. Done when: `make up` works on all three; RAM and first-start time written in README.

## Gateway and routing
- [x] **G1** P0 Add LiteLLM gateway service (pin the latest stable image tag from its releases page), per-user virtual keys, custom guardrail calling `brain /v1/inspect` (PRD 7, 8). Owner: Alexandros. Done when: an OpenAI SDK client with a personal key gets a masked-and-answered reply through the gateway; integration test passes.
- [x] **G2** P0 Unmask in answers + output filtering `/v1/inspect-output` (PRD 8). Owner: Alexandros.
- [x] **G3** P0 Warn (409 + ack header) and block (403) responses with reasons and approved alternative (PRD 8). Owner: Alexandros. Block verified by unit test only until D6 can trigger it live.
- [ ] **L1** P1 Local model: benchmark llama.cpp vs Ollama, 1B to 4B, Greek quality, on Sat 14; add the winner to compose, never on the critical path (PRD 21b). Owner: Stelios.
- [ ] **G4** P2 Anthropic-format endpoint (Claude Code demo). Owner: Alexandros.
- [ ] **M1** P2 MCP proxy with injection checks on tool results (PRD 9.5). Owner: Stelios.

## Detection
- [x] **D0** Validators (AFM, AMKA, IBAN, Luhn), normalisation, secrets regex, masking, policy precedence. (scaffold)
- [x] **D1** P0 Presidio + spaCy (en, el) for names, emails, phones; client names via aho-corasick from `clients` (PRD 9.2). Owner: Stelios.
- [x] **D2** P0 YARA rules for secrets and source code (`rules/*.yar`) (PRD 9.2). Owner: Stelios.
- [x] **D3** P0 Document registry: chunking, MinHash, embeddings (fastembed, ONNX), pgvector search, copy vs paraphrase (PRD 9.3). Owner: Stelios. **Go/no-go Sat 14**: recall on 20 Greek and English paraphrases.
- [ ] **D4** P0 File upload text extraction (PDF, DOCX) into the pipeline (PRD 9.1). Owner: Stelios.
- [ ] **D5** P1 Session memory: rebuild across prompts (PRD 9.4). Owner: Stelios.
- [ ] **D6** P1 Prompt-injection classifier (PRD 9.5). Owner: Stelios.
- [ ] **D7** P2 LLM judge for borderline scores, cached (PRD 9.6). Owner: Stelios.
- [x] **P1** P0 Policies from DB + `policies.yaml` seed, editable (PRD 10). Owner: Alexandros.

## Shadow AI, DNA, analyst
- [x] **O1** P0 `scripts/gen_org.py --seed 42` from `data/org/org.yaml`: users, keys, clients, documents, Squid + Zeek logs, incidents (PRD 21a). Owner: Stelios.
- [x] **O2** P0 Log ingest + AI tool inventory from `data/ai_tools.csv` (PRD 11). Owner: Stelios.
- [ ] **O3** P1 Employee simulator (`scripts/simulate.py`, compose profile `sim`) (PRD 21a). Owner: Stelios.
- [ ] **N1** P1 DNA marks: propose, approve, issue copies, attribution with confidence (PRD 12). Owner: Stelios.
- [x] **N2** P1 Sealed identity + two-person reveal + audit log (PRD 12). Owner: Alexandros.
- [x] **A1** P1 Analyst preset questions with SQL shown (PRD 13). Owner: Alexandros.
- [ ] **A2** P2 Free-text analyst questions over read-only views (PRD 13). Owner: Alexandros.

## Web (PRD 16)
- [x] **W1** P0 Company Chat: messages, five outcome chips, "Why?" disclosure, warn card, file upload. Owner: Alexandros.
- [x] **W2** P0 Security overview + inventory + incidents list. Owner: Alexandros.
- [x] **W3** P1 Incident detail: puzzle view, timeline, copy attribution, reveal request. Owner: Alexandros.
- [x] **W4** P1 Connect page: URL, personal key, snippets, live status. Owner: Alexandros.
- [x] **W5** P1 Policies and Documents pages. Owner: Alexandros.
- [x] **W6** P0 Responsive at 390 px + axe clean on every route. Owner: Alexandros.

## Evaluation and quality
- [ ] **E1** P0 `make eval`: report vs regex baseline, targets pass/fail (PRD 17, 18). Owner: Stelios.
- [ ] **E2** P1 promptfoo + garak red team, summary in report. Owner: Stelios.
- [ ] **E3** P1 Load test, latency p95 (PRD 17). Owner: Stelios.
- [x] **E4** P0 Integration tests through the gateway for all five outcomes (PRD 19). Owner: Alexandros.

## Team data (no code; edit files, then `make validate`)
- [ ] **T1** P0 `data/org/org.yaml`: company, 8 teams, 10 clients, AI habits, 14-day storyline. Owners: Konstantinos, Vasilis. Basics Fri 13, storyline Sat 14.
- [ ] **T2** P0 3 confidential documents in `data/documents/` (Greek + English). Owner: Konstantinos. Sat 14.
- [ ] **T3** P0 `data/eval/prompts.csv`: 60 rows by Sat 14, 200 by Mon 16. Owners: Konstantinos, Vasilis.
- [ ] **T4** P0 `data/ai_tools.csv`: about 15 tools rated. Owner: Vasilis. Sun 15.
- [ ] **T5** P1 Business pack in `docs/business/`: market, competitors, SWOT, pricing, roadmap, GDPR/AI Act, engagement. Owner: Vasilis. Mon 16 to Wed 18.

## Submission
- [ ] **R1** P0 README in the required parts (PRD 22) with measured numbers. Owners: Konstantinos (text), Alexandros (setup).
- [ ] **R2** P1 Video (private YouTube) linked at the top of README. Owner: Konstantinos with Alexandros. Thu 19.
- [ ] **R3** P1 Slides. Owner: Konstantinos. Draft Thu 19, final Tue 24.
- [ ] **R4** P0 Freeze Thu 19 20:00, submit Fri 20 by noon, judges have repo access. Owner: Alexandros.
