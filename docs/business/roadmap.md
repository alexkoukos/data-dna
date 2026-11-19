# Roadmap

**In repo** works today; **planned** does not exist yet.

## In repo
Gateway with five outcomes, layered detection, document matching with copy attribution, shadow-AI discovery from logs (synthetic), sealed identity, per-team policies, shadow mode and policy replay, compliance PDF, ROI view, weekly digest, tool-approval workflow, browser extension (chatgpt.com), SIEM export (JSON lines, CEF syslog, signed webhook), MCP proxy, split storage for sensitive fields.

## Next
1. **Slack and Teams** (planned). Check and mask messages to AI assistants inside the tools people already use.
2. **More languages** (planned). German and French are lighter than Greek and English; add Spanish, Italian and others with their national ID formats, and test paraphrase recall per language.
3. **Small-company edition** (planned). One container, a setup wizard, a managed local model, a flat price.
4. **Login and roles** (planned, needed before any pilot). Real sign-on and per-role access to the dashboard and API; today the demo has none.
5. **More browser coverage** (planned). Other AI sites, file uploads and images in the extension.
6. **Split storage in the app** (planned). Use it for names behind the sealed identity and any salary-like data; today it is a tested library with demo and API routes.
7. **Per-customer tuning** (planned). Calibration from shadow mode with a report per company.
8. **Third-party review** (planned). Penetration test and a data protection impact assessment template.

## What would change the order
A pilot customer who mostly uses web chat tools moves browser coverage up; one who is mostly developers moves agent and MCP coverage up. We decide after five buyer conversations ([business-case.md](business-case.md)).
