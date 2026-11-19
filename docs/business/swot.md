# SWOT (T5)

## Strengths
- One gate for chat, API, agents and MCP, with five outcomes (allow, warn, mask, answer locally, block) instead of only "block".
- Catches rewritten confidential documents, not only patterns; Greek identifiers (AFM, AMKA, IBAN) validated by checksum.
- Runs from `docker compose up`, works without any cloud key (local model fallback), data stays in the company.
- Privacy built in: fingerprints not text, sealed identity with two-person reveal, audit log, retention limit, and split storage of sensitive fields (two vaults, integrity tags).
- Every decision is explained ("Why?"), and shadow mode measures false alarms before enforcing.

## Weaknesses
- Hackathon-stage product: demo mode has no login; the brain API is unauthenticated (see `docs/THREAT_MODEL.md`).
- Detection is probabilistic and measured on synthetic data only; paraphrase recall is about 7 in 10 (`docs/calibration.md`).
- Only covers traffic that goes through the gateway or appears in logs.
- No certifications, no reference customers, a four-person team.
- Greek and English are strongest; other languages are shallow.

## Opportunities
- EU rules push companies to show control over AI use: AI literacy (AI Act Art. 4) is already in force, NIS2 requires risk handling, and GDPR duties apply to what is sent to AI vendors (`privacy-and-regulation.md`).
- Surveys show a large share of staff already use unapproved AI (`market.md`), and most firms in IBM's study had no AI governance policy.
- Mid-size European firms are too small for the big DLP suites and too regulated to do nothing.
- Local models are now good enough to answer confidential questions inside the company.

## Threats
- Big suites (Microsoft, Netskope, Zscaler) add AI controls to products customers already own.
- Browser vendors and AI providers add their own enterprise controls (company workspaces, data-loss settings).
- Attackers adapt to detection; evasion is an arms race, and a miss is a visible failure.
- Rules and dates change; for example the EU AI Act timeline has been amended and needs rechecking before any claim to a customer.
