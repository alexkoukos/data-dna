# Market and the problem in numbers (T5)

Written for the judges and a first customer. Every figure has a source and a caveat. Surveys and market forecasts disagree widely, so each is shown as a range or a direction, not as a fact about our own product. Nothing here is a measurement of Sentry.

## The problem: employees already put company data into AI tools
| Figure | What it measures | Source |
|---|---|---|
| About 18% of enterprise employees paste data into generative AI tools (LayerX telemetry) | Observed behaviour in browsers, the most behaviour-based number we found | [LayerX Enterprise AI and SaaS Data Security Report 2025, as summarised by TechRadar](https://www.techradar.com/pro/security/watch-out-your-workers-might-be-pasting-company-secrets-into-chatgpt) |
| 57% of employees at large US enterprises say they entered confidential company data into AI tools (TELUS Digital, Jan 2025) | Self-reported, online panel | [Dataconomy summary](https://dataconomy.com/2025/02/28/57-percent-of-employees-expose-sensitive-data-to-genai/) |
| 49% of 2,000 surveyed workers adopted AI tools without employer approval (BlackFog) | Self-reported use of unapproved tools | [Managers turn blind eye to unapproved AI use](https://fintech.global/2025/10/08/managers-turn-blind-eye-to-unapproved-ai-use/) |

Read as a range: roughly 1 in 5 people observed pasting, and about half admitting unapproved use or confidential sharing. Do not quote one number as "the" rate. The widely shared "77%" headline is about the share of LLM access that goes to ChatGPT, not the share of staff who leak data.

## What a leak costs
- The global average cost of a data breach was **USD 4.44 million** in 2025, down from 4.88 million in 2024 (IBM and Ponemon). [IBM](https://www.ibm.com/think/x-force/2025-cost-of-a-data-breach-navigating-ai), [Help Net Security](https://helpnetsecurity.com/2025/08/04/ibm-cost-data-breach-report-2025)
- Organisations with a high level of shadow AI paid about **USD 670,000 more** per breach than those with little or none; shadow AI was involved in about 20% of breaches. One outlet reports a different premium (USD 200,000), so treat the 670,000 as IBM's headline figure and check the PDF before quoting it on a slide. [Mondaq](https://www.mondaq.com/unitedstates/new-technology/1670940/the-ai-oversight-gap-ibms-2025-data-breach-report-reveals-hidden-costs-of-ungoverned-ai)
- 63% of the organisations in the same study had no AI governance policy. [TechRepublic](https://www.techrepublic.com/article/news-ai-breach-risks-rise-as-governance-lags/)

These are global, mostly breach-wide averages, not the price of one pasted prompt. Our own ROI view uses far smaller, invented per-incident costs (see `roi-assumptions.md`).

## Size of the market
No source gives a clean "AI data leak prevention" market. Forecasts for 2030 depend on how each firm draws the line:

| Definition | 2030 forecast | Source |
|---|---|---|
| AI systems security (narrow) | nearly USD 8 billion | [Dell'Oro via ICT Business](https://www.ictbusiness.biz/analysis/ai-security-market-forecast-to-reach-8-billion-by-2030) |
| AI trust, risk and security management | USD 7.44 billion, 21.6% a year | [Grand View Research via Security World Market](https://www.securityworldmarket.com/na/News/Business-News/booming-market-for-securing-ai-predicted-at-216-cagr-to-2030) |
| Generative AI cybersecurity (wider) | USD 40.1 billion, 33.4% a year (another page of the same publisher gives a lower base, USD 14.5 billion) | [MarketsandMarkets](https://marketsandmarkets.com/PressReleases/generative-ai-cybersecurity.asp) |

Honest reading: the space is in the single-digit to tens of billions of USD by 2030 and growing about 20 to 35% a year, depending on definition. We do not claim a share of it. Our reachable slice is the part of it that is a gateway plus data-leak control for mid-size European firms, which none of these reports sizes.

## Who feels it first
Organisations that hold other people's confidential data and are under EU rules: law firms, consultancies, banks and insurers, public bodies, and IT service companies like the hackathon sponsor. They have a CISO or DPO, a policy that says "do not paste client data into public AI", and no way to see whether anyone follows it. See `customer-and-pricing.md`.
