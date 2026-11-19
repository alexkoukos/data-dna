# Customer, price and how we sell (T5)

All prices here are a **hypothesis to test with real buyers**. We have not studied competitors' prices and do not quote them. Figures are in EUR.

## Who buys
- **Buyer:** the CISO or head of IT security; the DPO signs off. The budget comes from security or compliance.
- **First segments:** law firms and consultancies (client confidentiality is the product), banks and insurers (regulated, Greek identifiers everywhere), IT service companies (client code and secrets), public bodies.
- **Size:** 200 to 5,000 employees. Smaller firms get the simple version (below); larger ones already run a DLP suite and need a reason to add a gateway.
- **The trigger:** a policy that says "do not paste client data into AI", an audit question about AI use, or an incident.

## What they get, by tier (proposal)
| Tier | For | Includes | Price idea |
|---|---|---|---|
| Starter | up to 200 staff | Gateway, detection, five outcomes, dashboard, local model, one policy set; self-hosted with Docker | about 4 EUR per user per month, minimum 400 EUR per month |
| Business | 200 to 2,000 | Adds document matching, DNA marks, shadow-AI discovery from logs, teams and role policies, weekly summary, webhook alerts | about 8 EUR per user per month |
| Enterprise | 2,000+ | Adds single sign-on, SIEM export, retention and audit settings, support terms, on-premises help | per contract, from about 6 EUR per user per month at volume |

Why per user per month: it matches how security and AI tools are bought, and cost grows with the number of people at risk. Self-hosting means we do not carry their data or model costs.

## Checking that it pays for itself
The dashboard's ROI view (`docs/business/roi-assumptions.md`) shows cost avoided from stopped incidents. Its unit costs are invented and cautious. A pilot should replace them with the customer's own figures. Rule of thumb for the pitch: for a 500-person firm on the Business tier the price is about 48,000 EUR a year; against IBM's average breach cost of USD 4.44 million (`market.md`) that is roughly 1% of one average breach. This is an illustration, not a promise: most firms never suffer an average breach.

## How we sell
1. **Shadow mode first.** Install, let every message through for two to four weeks, and show "would have blocked N" per team and tool. No risk for the buyer and no employee impact.
2. **Show the unknown tools.** Log ingest lists the AI tools nobody approved; this is usually the moment the CISO asks for more.
3. **Turn on enforcement per category**, starting with secrets and identifiers, then documents.
4. **Prove it for the auditor:** the compliance PDF and incident log (`compliance-mapping.md`).
5. **Channel:** IT consultancies and integrators who already run security projects for these firms (the sponsor's own business is an example).

## What we have not validated
No customer has been interviewed, no price tested, no pilot run. The first step after the hackathon is five buyer conversations to check the tiers and the shadow-mode pitch.
