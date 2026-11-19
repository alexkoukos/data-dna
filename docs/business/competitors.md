# Competitors and SWOT

Categories and positioning come from vendors' public descriptions as we understand them. **We have not tested any of these products**; features change, so verify before quoting. "Sentry" means what is in this repo, measured by `make eval`.

| Category | Examples | Strong at | Weak for this problem | Where Sentry sits |
|---|---|---|---|---|
| Classic DLP and CASB | Microsoft Purview, Netskope, Zscaler, Symantec | Pattern and label control across email, files, cloud apps; already owned by large firms | Built before chat prompts: weak on rewritten text, little explanation to the employee, heavy to deploy | Catches a rewritten document, answers locally instead of only blocking, explains each decision |
| Browser-side AI security | LayerX, Harmonic | See what people type into AI sites, including unsanctioned tools | An extension on every browser; sees the page, not API and agent traffic | The gateway covers apps, scripts and agents. Our browser extension covers one site (chatgpt.com); other web tools are seen only in network logs |
| AI gateways and guardrails | LiteLLM, Cloudflare AI Gateway, Lakera, Nightfall, Presidio | Routing, keys, budgets, PII and injection checks | Mostly pattern and PII; little on company documents, shadow tools or who may reveal a name | Built on LiteLLM and Presidio-style checks, adds document matching, session memory, shadow-AI discovery and sealed identity |
| Leak tracing | EchoMark, AuthMark | Mark documents so a leak points to a person | After the fact; do not stop the paste | DNA marks trace a copy, and the gate stops the paste |
| Policy only | Acceptable-use PDF, training | Cheap | No visibility, no enforcement | Shadow mode shows what would have happened before enforcing |

**Our claim, kept narrow.** No single product above does all of: discover hidden AI tools from logs, catch paraphrased documents, route confidential content to a local model, and trace a leaked copy, with a sealed identity and audit trail. Each part exists elsewhere, often more mature.

## SWOT

**Strengths**
- One gate for chat, API, agents and MCP, with five outcomes instead of only "block".
- Catches rewritten confidential documents; Greek identifiers validated by checksum.
- Runs from `docker compose up` with no cloud key; data stays in the company.
- Privacy built in: fingerprints not text, sealed identity, audit log, retention, split storage.
- Every decision is explained; shadow mode measures false alarms before enforcing.

**Weaknesses**
- Hackathon stage: demo mode has no login ([THREAT_MODEL.md](../THREAT_MODEL.md)).
- Detection is probabilistic and measured on synthetic data ([EVALUATION.md](../EVALUATION.md)).
- Only covers traffic through the gateway, the extension or logs.
- No certifications or reference customers; four-person team.
- Greek and English are strongest; other languages are shallow.

**Opportunities**
- EU rules push firms to show control over AI use: AI literacy (AI Act Art. 4), NIS2 risk handling, GDPR duties for data sent to AI vendors ([compliance.md](compliance.md)).
- Large shares of staff already use unapproved AI ([business-case.md](business-case.md)).
- Mid-size European firms are too small for big DLP suites and too regulated to do nothing.
- Local models are now good enough to answer confidential questions in-house.

**Threats**
- Big suites add AI controls to products customers already own.
- Browser vendors and AI providers add their own enterprise controls.
- Evasion is an arms race, and a miss is a visible failure.
- Rules and dates change; the EU AI Act timeline has been amended and needs rechecking before any claim to a customer.
