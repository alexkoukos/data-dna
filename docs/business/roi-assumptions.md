# ROI assumptions (X18)

The ROI view (`GET /v1/roi`, page "ROI" in the security area) estimates the cost avoided by what Sentry stopped. It is an estimate built from the assumptions below, not a measurement. The numbers are illustrative and invented for the demo. Replace them with the company's own figures before showing anyone a total. Source in code: `services/brain/src/brain/insights.py` (`UNIT_COST_EUR`, `DOC_COST_EUR`, `LIKELIHOOD`). Change this file and the code together.

## How it is computed
1. Take incidents in the window (default 30 days) whose outcome stopped data leaving: **Masked, Answered locally, Blocked**. Warned incidents are not counted, because the person may still have sent the message. Incidents recorded in shadow mode are shown separately as "would have stopped".
2. For each incident, take the **single most expensive** item involved (not the sum, so one prompt is not counted twice): the cost of its data type, or of the matched document's sensitivity.
3. Add them up: this is the **exposure**.
4. Multiply by **likelihood**: the share of stopped leaks assumed to have become a real incident. This is **cost avoided**.

## Assumptions (EUR per incident)
| Data type | Cost | Why this order of magnitude |
|---|---|---|
| Secret or API key | 5000 | Rotate the key, audit its use, possible provider charges |
| Honeytoken (a planted decoy was pasted) | 8000 | A confirmed leak of a confidential document |
| Source code | 2000 | Code review, rewrite of exposed parts |
| Client name | 1500 | Contract and trust impact |
| Card number | 200 | Card reissue and fraud monitoring |
| IBAN, AFM/AMKA/ID | 150 | Notification and monitoring effort per person |
| Email, phone | 100 | Low per-person effort |
| Prompt injection | 300 | Triage and clean-up |

| Matched document | Cost |
|---|---|
| Restricted | 10000 |
| Confidential | 4000 |
| Internal | 500 |

**Likelihood: 10%.** Most prompts that contain a sensitive value never become a reportable breach. 10% is deliberately cautious, so the headline figure is not inflated. A reader who disagrees can multiply the exposure line by their own rate.

## Risk per tool
`risk score = risk weight × requests`, where the weight is low 1, medium 2, high 3, critical 4, and one lower for tools the company has approved. It only ranks tools for attention; it is not a probability.

## Limits, stated plainly
- The unit costs are not taken from a study. Do not quote the total as a fact.
- Only incidents the gateway saw are counted. Shadow AI that bypasses the gateway is in the tool inventory, not here.
- Open for the business owner (Vasilis): replace the table with the company's figures, or cite a source for each row.
