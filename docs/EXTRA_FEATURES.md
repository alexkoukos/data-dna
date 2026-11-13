# Extra features (X1 to X26)

These sit on top of the P0 and P1 items in `TASKS.md`. A feature counts only if it has tests and one paragraph in the README. Priority: **P1** if the core works, **P2** is cut first.
Suggested order: X1, X2, X4, X5, X11, X17, X23. All small, no new infrastructure, and visible in a demo.

Owners: every technical item is Alexandros. Vasilis and Konstantinos keep the data, business and writing items.
Status: `[ ]` open, `[~] (name)` in progress, `[x]` done.

## 1. Break it (red team)
- [x] **X1** P1 "Try to break it" page: type anything, see the decision, the reasons and which layer caught it. Playwright test with 10 evasions. Owner: Alexandros.
- [x] **X2** P1 Attack file `data/eval/attacks.csv`, 80 rows with the expected result. Feeds `make eval` and the page. Owner: Vasilis and Konstantinos (data); Alexandros wires it into eval.
- [ ] **X3** P2 Table of the judges' attempts during the demo (in memory). Owner: Alexandros.

## 2. Detection depth
- [x] **X4** P1 Honeytokens: fake keys and details planted in confidential documents. If one shows up in a prompt, raise an alarm with no false alarms. Owner: Alexandros.
- [x] **X5** P1 Greeklish and mixed scripts: names and AFM in Latin letters, or with look-alike characters (A/Α, o/ο). Target recall at least 80%. Owner: Alexandros.
- [ ] **X6** P1 More Greek identifiers: ADT, number plates, +30 phones, GEMI, passport. Owner: Alexandros.
- [ ] **X7** P1 Check the model's answers for leaks before they reach the user. Owner: Alexandros.
- [ ] **X8** P2 Images and screenshots: OCR, then the same checks (RapidOCR, ONNX). Owner: Alexandros.
- [ ] **X9** P2 Code leaks: source-code fingerprints (winnowing) on top of YARA. Owner: Alexandros.
- [ ] **X10** P2 Document matching also in German and French for international clients. Owner: Alexandros.

## 3. Policy and operations
- [ ] **X11** P1 Shadow mode: the policy records what it would have done without blocking, with a "would have blocked N" view. Owner: Alexandros.
- [ ] **X12** P1 Try a new policy on the last 14 days of prompts before saving it. Owner: Alexandros.
- [ ] **X13** P1 Policies per group and role (HR sees salaries, Sales does not). Owner: Alexandros.
- [ ] **X14** P2 Rate and spend limits per user key. Owner: Alexandros.
- [ ] **X15** P2 Slack or Teams webhook alerts for critical incidents, off by default. Owner: Alexandros.
- [ ] **X16** P2 Delete old data by `RETENTION_DAYS`, with a test. Owner: Alexandros.

## 4. Business and compliance
- [ ] **X17** P1 One-click PDF compliance report mapped to GDPR, NIS2 and the EU AI Act. Mapping table in `docs/business/`. Owner: Vasilis (table), Alexandros (export).
- [ ] **X18** P1 ROI view: leaks stopped, estimated cost avoided (documented assumptions), risk per tool. Owner: Vasilis (assumptions), Alexandros (view).
- [ ] **X19** P2 Employee coaching: a warning suggests a safe rewrite and we count how many accept it. Owner: Alexandros.
- [ ] **X20** P2 Weekly summary for the CISO. Owner: Alexandros.

## 5. Prevention outside the gateway
- [ ] **X21** P2 Paste guard: a small local program that watches the clipboard, calls `/v1/inspect` and offers the masked version. Not part of `docker compose`. Owner: Alexandros.
- [ ] **X22** P2 Guide for pointing a company's AI traffic at the gateway (env vars, base URL, Squid ICAP sketch). Owner: Konstantinos.

## 6. Trust and explanation
- [ ] **X23** P1 "Why?" on every decision: which layers fired and with what score, stored on the incident. Owner: Alexandros.
- [ ] **X24** P1 History per employee and per document, replaying the (masked) prompts. Owner: Alexandros.
- [ ] **X25** P2 `scripts/calibrate.py`: calibrate thresholds without training, with a chart in `docs/`. Owner: Alexandros.
- [ ] **X26** P2 `docs/THREAT_MODEL.md`: what we stop, what we do not, honest limits. Owner: Konstantinos.

## Rules
- The P0 items in `TASKS.md` finish first. The X items start after.
- Every X has a test, one README paragraph and, if it touches data, synthetic data only.
- A few features that work and show beat many half-finished ones.
