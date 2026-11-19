# Business case

The problem in numbers, who buys, what it costs, and how the ROI view is computed. Every external figure has a source and a caveat. Surveys and forecasts disagree widely, so each is shown as a range. Prices and unit costs are hypotheses: no customer has been interviewed and no pilot run.

## The problem: staff already put company data into AI tools

| Figure | What it measures | Source |
|---|---|---|
| About 18% of enterprise employees paste data into generative AI tools | Observed in browsers (LayerX telemetry) | [LayerX report 2025, via TechRadar](https://www.techradar.com/pro/security/watch-out-your-workers-might-be-pasting-company-secrets-into-chatgpt) |
| 57% of employees at large US enterprises say they entered confidential data into AI tools | Self-reported (TELUS Digital, Jan 2025) | [Dataconomy](https://dataconomy.com/2025/02/28/57-percent-of-employees-expose-sensitive-data-to-genai/) |
| 49% of 2,000 surveyed workers used AI tools without employer approval | Self-reported (BlackFog) | [Fintech Global](https://fintech.global/2025/10/08/managers-turn-blind-eye-to-unapproved-ai-use/) |

Read as a range: roughly 1 in 5 observed pasting, and about half admitting unapproved use or confidential sharing. Do not quote one number as "the" rate.

**What a leak costs.** The global average cost of a data breach was USD 4.44 million in 2025 (IBM and Ponemon). Organisations with high shadow AI paid about USD 670,000 more per breach, and 63% had no AI governance policy ([IBM](https://www.ibm.com/think/x-force/2025-cost-of-a-data-breach-navigating-ai), [Mondaq](https://www.mondaq.com/unitedstates/new-technology/1670940/the-ai-oversight-gap-ibms-2025-data-breach-report-reveals-hidden-costs-of-ungoverned-ai), [TechRepublic](https://www.techrepublic.com/article/news-ai-breach-risks-rise-as-governance-lags/)). One outlet reports a different premium, so check the IBM PDF before quoting 670,000. These are breach-wide averages, not the price of one pasted prompt.

**Market size.** No source sizes "AI data leak prevention" cleanly. 2030 forecasts range from nearly USD 8 billion for AI systems security ([Dell'Oro](https://www.ictbusiness.biz/analysis/ai-security-market-forecast-to-reach-8-billion-by-2030)) and USD 7.44 billion for AI trust, risk and security management ([Grand View](https://www.securityworldmarket.com/na/News/Business-News/booming-market-for-securing-ai-predicted-at-216-cagr-to-2030)) to USD 40.1 billion for generative-AI cybersecurity ([MarketsandMarkets](https://marketsandmarkets.com/PressReleases/generative-ai-cybersecurity.asp)), growing about 20 to 35% a year. We claim no share. Our slice is gateway-plus-data-leak control for mid-size European firms, which none of these reports sizes.

## Who buys

- **Buyer:** the CISO or head of IT security; the DPO signs off.
- **First segments:** law firms and consultancies (client confidentiality is the product), banks and insurers (regulated, Greek identifiers everywhere), IT service companies (client code and secrets), public bodies.
- **Size:** 200 to 5,000 employees. Smaller firms get a simple version; larger ones already run a DLP suite and need a reason to add a gateway.
- **Trigger:** a policy that says "do not paste client data into AI", an audit question, or an incident.

## Price (proposal)

| Tier | For | Includes | Price idea |
|---|---|---|---|
| Starter | up to 200 staff | Gateway, detection, five outcomes, dashboard, local model, one policy set; self-hosted | about 4 EUR per user per month, minimum 400 EUR per month |
| Business | 200 to 2,000 | Adds document matching, DNA marks, shadow-AI discovery, team and role policies, weekly digest, alerts | about 8 EUR per user per month |
| Enterprise | 2,000+ | Adds single sign-on, SIEM export, retention and audit settings, support terms | per contract, from about 6 EUR per user per month |

Per user per month matches how security tools are bought. Self-hosting means we carry no customer data or model cost. For a 500-person firm on Business the price is about 48,000 EUR a year, roughly 1% of IBM's average breach cost. That is an illustration, not a promise.

## How we sell

1. **Shadow mode first.** Install, let everything through for two to four weeks, show "would have blocked N" per team and tool.
2. **Show the unknown tools.** The tool inventory lists AI tools nobody approved.
3. **Enforce per category**, starting with secrets and identifiers, then documents.
4. **Prove it for the auditor** with the compliance PDF and incident log ([compliance.md](compliance.md)).
5. **Channel:** IT consultancies and integrators that already run security projects for these firms.

## Why employees will use it

A control people route around fails, so the gate has to be the easier way to use AI. It answers instead of refusing (confidential questions go to the local model); it masks and restores values so people do not clean their text; it explains every outcome in plain words; it offers a safer rewrite in one click; and it gives access to strong models without a personal account. These are hypotheses to test in a pilot: share of messages allowed unchanged, acceptance of the safe rewrite, and whether use moves from unapproved tools to the gate.

## ROI view

`GET /v1/roi` (page "Impact") estimates cost avoided. It is an estimate from invented, deliberately cautious unit costs; replace them with the customer's own figures before showing a total. Code: `services/brain/src/brain/insights.py` (`UNIT_COST_EUR`, `DOC_COST_EUR`, `LIKELIHOOD`); change this table and the code together.

1. Take incidents in the window (default 30 days) that stopped data leaving: masked, answered locally, blocked. Warnings are not counted. Shadow-mode incidents are shown separately as "would have stopped".
2. For each, take the single most expensive item involved (not the sum): its data type or the matched document's sensitivity.
3. Add them: the **exposure**. Multiply by the **likelihood, 10%**, the assumed share that would have become a real incident: the **cost avoided**.

| Data type | EUR | | Matched document | EUR |
|---|---|---|---|---|
| Honeytoken pasted | 8000 | | Restricted | 10000 |
| Secret or API key | 5000 | | Confidential | 4000 |
| Source code | 2000 | | Internal | 500 |
| Client name | 1500 | | | |
| Prompt injection | 300 | | | |
| Card number | 200 | | | |
| IBAN, AFM, AMKA, ID | 150 | | | |
| Email, phone | 100 | | | |

Per-tool risk score = weight (low 1, medium 2, high 3, critical 4, one lower if approved) x requests. It ranks tools for attention; it is not a probability. Only incidents the gateway saw are counted.
