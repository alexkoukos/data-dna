# Competitors (T5)

Categories and positioning come from the vendors' public descriptions as we understand them. **We have not tested any of these products**, and features change; verify before quoting. "Pyli today" means what is in this repo and is measured by `make eval`, not a plan.

| Category | Examples | What they do well | What they do not (for this problem) | Where Pyli sits |
|---|---|---|---|---|
| Classic DLP and CASB | Microsoft Purview, Netskope, Zscaler, Symantec | Pattern and label based control across email, files, cloud apps; already bought by large firms | Built before chat prompts: weak on rewritten text, little explanation to the employee, heavy to deploy, often priced per suite | We catch a **rewritten** confidential document (paraphrase matching), answer locally instead of only blocking, and explain each decision in plain words |
| Browser-side AI security | LayerX, Harmonic and similar | See what people type into AI sites in the browser, including unsanctioned tools | Needs an extension on every browser; sees the page, not the company's own API and agent traffic | We sit at the gateway, so apps, scripts and agents are covered too. Their strength is coverage of web tools we only get through network logs. The extension is on our roadmap |
| AI gateways and guardrails | LiteLLM, Cloudflare AI Gateway, Lakera, Nightfall, Presidio (open source) | Routing, keys, budgets, PII and prompt-injection checks | Mostly pattern and PII checks; little about company documents, shadow tools, or who must approve revealing a name | We build on LiteLLM and Presidio and add document matching, session memory, shadow-AI discovery from logs and sealed identity |
| Leak tracing | EchoMark, AuthMark and similar | Mark documents so a leaked copy points to a person | Trace after the fact; do not stop the paste | DNA marks give the same traceability **and** the gateway stops the paste |
| Policy only | Acceptable-use PDF, training | Cheap, sets expectations | No visibility, no enforcement | Shadow mode shows what would have happened before enforcing anything |

## Our claim, kept narrow
No single product above does all of: discover hidden AI tools from logs, catch paraphrased documents, route confidential content to a local model, and trace a leaked copy to a recipient, with a sealed identity and an audit trail. That combination is our difference. Each part alone exists elsewhere, often more mature.

## Where we are weaker
- Maturity, support, integrations and certifications (SOC 2, ISO 27001): none yet.
- Coverage of traffic that bypasses the gateway (see `docs/THREAT_MODEL.md`).
- Detection is probabilistic; our numbers are on synthetic data (`make eval`), not customer data.
- Languages: Greek and English well, German and French lighter, others by exact copy only.
