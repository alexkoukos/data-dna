# Roadmap: future usage (T5)

Status words are honest: **in repo** means it works today, **planned** means it does not exist yet.

## Already in the repo
Gateway with five outcomes, detection layers, document matching, shadow-AI discovery from logs (synthetic), DNA marks, sealed identity, policies per team, shadow mode, compliance PDF, ROI view, split storage for sensitive fields.

## Next five steps
1. **Browser extension** (planned). Covers web chat tools that never touch our gateway and gives a warning at the moment of pasting. Biggest gap in `docs/THREAT_MODEL.md`.
2. **Slack and Teams** (planned). Check and mask messages to AI assistants inside the chat tools people already use.
3. **SIEM and ticket export** (planned). Send incidents to Splunk, Sentinel or similar, so the security team works in its own tools. A webhook alert exists today.
4. **More languages** (planned). German and French are lighter than Greek and English; add Spanish, Italian and others with their national ID formats, and test paraphrase recall per language.
5. **Version for small companies** (planned). One container, a setup wizard, a managed local model, and a flat price. Also a login and roles: today the demo has none.

## Also on the list
- Real sign-on and per-role access to the dashboard (needed before any customer pilot).
- Use split storage for the most sensitive fields in the app itself (names behind the sealed identity, any salary-like data); today it is a tested library with demo and API routes.
- Customer-specific tuning from shadow mode, with a calibration report per company.
- Third-party review: penetration test and a data protection impact assessment template for customers.

## What would change the order
A pilot customer who mostly uses web chat tools moves the extension to step 1; one who is mostly developers moves agent and MCP coverage up. We decide after the first five buyer conversations (`customer-and-pricing.md`).
