# Extra features (X1 to X29)
# Extra features (X1 to X26, X30)
# Extra features (X1 to X26, X31)
# Extra features (X1 to X26, X32)

These sit on top of the P0 and P1 items in `TASKS.md`. A feature counts only if it has tests and one paragraph in the README. Priority: **P1** if the core works, **P2** is cut first.
Suggested order: X1, X2, X4, X5, X11, X17, X23. All small, no new infrastructure, and visible in a demo.

Owners: every technical item is Alexandros. Vasilis and Konstantinos keep the data, business and writing items.
Status: `[ ]` open, `[~] (name)` in progress, `[x]` done.

## 1. Break it (red team)
- [x] **X1** P1 "Try to break it" page: type anything, see the decision, the reasons and which layer caught it. Playwright test with 10 evasions. Owner: Alexandros.
- [x] **X2** P1 Attack file `data/eval/attacks.csv`, 80 rows with the expected result. Feeds `make eval` and the page. Owner: Vasilis and Konstantinos (data); Alexandros wires it into eval.
- [x] **X3** P2 Table of the judges' attempts during the demo (in memory). Owner: Alexandros.

## 2. Detection depth
- [x] **X4** P1 Honeytokens: fake keys and details planted in confidential documents. If one shows up in a prompt, raise an alarm with no false alarms. Owner: Alexandros.
- [x] **X5** P1 Greeklish and mixed scripts: names and AFM in Latin letters, or with look-alike characters (A/Α, o/ο). Target recall at least 80%. Owner: Alexandros.
- [x] **X6** P1 More Greek identifiers: ADT, number plates, +30 phones, GEMI, passport. Owner: Alexandros.
- [x] **X7** P1 Check the model's answers for leaks before they reach the user. Owner: Alexandros.
- [x] **X8** P2 Images and screenshots: OCR, then the same checks (RapidOCR, ONNX). Owner: Alexandros.
- [x] **X9** P2 Code leaks: source-code fingerprints (winnowing) on top of YARA. Owner: Alexandros.
- [x] **X10** P2 Document matching also in German and French for international clients. Owner: Alexandros.

## 3. Policy and operations
- [x] **X11** P1 Shadow mode: the policy records what it would have done without blocking, with a "would have blocked N" view. Owner: Alexandros.
- [x] **X12** P1 Try a new policy on the last 14 days of prompts before saving it. Owner: Alexandros.
- [x] **X13** P1 Policies per group and role (HR sees salaries, Sales does not). Owner: Alexandros.
- [x] **X14** P2 Rate and spend limits per user key. Owner: Alexandros.
- [x] **X15** P2 Slack or Teams webhook alerts for critical incidents, off by default. Owner: Alexandros.
- [x] **X16** P2 Delete old data by `RETENTION_DAYS`, with a test. Owner: Alexandros.

## 4. Business and compliance
- [x] **X17** P1 One-click PDF compliance report mapped to GDPR, NIS2 and the EU AI Act. Mapping table in `docs/business/`. Owner: Vasilis (table), Alexandros (export).
- [x] **X18** P1 ROI view: leaks stopped, estimated cost avoided (documented assumptions), risk per tool. Owner: Vasilis (assumptions), Alexandros (view).
- [x] **X19** P2 Employee coaching: a warning suggests a safe rewrite and we count how many accept it. Owner: Alexandros.
- [x] **X20** P2 Weekly summary for the CISO. Owner: Alexandros.

## 5. Prevention outside the gateway
- [x] **X21** P2 Paste guard: a small local program that watches the clipboard, calls `/v1/inspect` and offers the masked version. Not part of `docker compose`. Owner: Alexandros.
- [x] **X22** P2 Guide for pointing a company's AI traffic at the gateway (env vars, base URL, Squid ICAP sketch). Owner: Konstantinos.
- [x] **X27** P1 Browser extension for personal ChatGPT (Chrome or Edge, `chatgpt.com`): checks paste and send with `/v1/inspect`, masks, warns, blocks or records in shadow mode, and fails open with a "Pyli offline" badge. Key-to-user lookup and extension-only CORS in the brain. Owner: Alexandros.
- [x] **X28** P1 Break it leaderboard and self-growing attack set: `/break-it` shows today's attempts, stopped, got through and catch rate (misses by masked preview and kind only), an optional nickname for a top-breakers list, and "It got through", which sends the text to a review queue (Security, "Break it review"). Approved rows are appended to `data/eval/attacks_scripts.csv` with `source=breakit` and the date; rejected rows are deleted at once; `make eval` reports them as "found live, still missed: N". Owner: Alexandros.
- [x] **X29** P1 Request and approve an AI tool: an employee asks from the Chat page (or from the block card), security decides on the new "Requests" tab of the AI tools page with a risk rating, the data categories the tool may receive and an optional alternative. Approval updates `ai_tools` (so the inventory and risk per tool change at once), every step goes to `audit_log`, and the requester sees the outcome on their next message. Owner: Alexandros.
- [x] **X30** P1 SIEM export: `GET /v1/export/incidents?since=` (JSON lines), optional syslog sender in CEF (UDP or TCP) and optional HMAC-signed webhook, set in `.env`. Events hold the user key ID, team, tool, decision, categories, document ID and rule IDs, never prompt text or a masked preview. `docs/siem/` has a Sigma rule and Splunk and Elastic examples; compose profile `siem` (`make siem`) shows events arriving. Owner: Alexandros.
- [x] **X31** P1 "Send it to Company AI instead": on a block or warning in Company Chat, one button resends the message with `X-DNA-Reroute: 1`. The gate masks it and answers on the company model (never the original destination), the answer is marked "Answered by Company AI", and the incident becomes "rerouted" (counted as stopped in the ROI view and the compliance evidence). Injection attempts, decoy credentials and document rebuilds cannot be rerouted. Owner: Alexandros.
- [x] **X32** P2 Weekly team digest: one page per team lead for the last 7 days (counts per outcome and per kind of data, top tools approved or not, the trend against the week before, and 2 or 3 "do this instead" tips from the kinds of data that fired). Team-level counts only, said at the top. Built from SQL over the read-only views and fixed templates, no model call. "Digest" tab in Security with "Copy as email" and a Markdown download; nothing is emailed. Owner: Alexandros.

## 6. Trust and explanation
- [x] **X23** P1 "Why?" on every decision: which layers fired and with what score, stored on the incident. Owner: Alexandros.
- [x] **X24** P1 History per employee and per document, replaying the (masked) prompts. Owner: Alexandros.
- [x] **X25** P2 `scripts/calibrate.py`: calibrate thresholds without training, with a chart in `docs/`. Owner: Alexandros.
- [x] **X26** P2 `docs/THREAT_MODEL.md`: what we stop, what we do not, honest limits. Owner: Konstantinos.

## Rules
- The P0 items in `TASKS.md` finish first. The X items start after.
- Every X has a test, one README paragraph and, if it touches data, synthetic data only.
- A few features that work and show beat many half-finished ones.
