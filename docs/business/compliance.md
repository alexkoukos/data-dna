# Privacy and compliance

What Sentry does to stay within GDPR, NIS2 and the EU AI Act, and which duty each control helps with. The same table is built into the one-click PDF report (`GET /v1/compliance-report.pdf`, source `services/brain/src/brain/compliance.py`). It supports a company's own compliance work. It is not legal advice and certifies nothing: a lawyer or DPO should confirm how each duty applies.

## A watcher must be careful with what it watches

A tool that reads every prompt is itself a privacy risk, so it keeps little:

- **Less data.** Sensitive values are masked before a prompt reaches a cloud model. Incidents store entity names, categories and masked previews, not the prompt (GDPR Art. 5(1)(c)).
- **Fingerprints, not text** for registered documents.
- **Names stay sealed.** Incidents show a pseudonym. A real name appears only after one person asks with a reason and a different person approves; each step is audited (Art. 5(1)(f), 25, 32).
- **Deletion.** Records are purged after `RETENTION_DAYS` (default 30), also on demand.
- **Local for confidential content.** The local model answers, so the text does not leave the company (Chapter V transfers).
- **Split storage** for the most sensitive fields: two shares in two separate databases with integrity tags.
- **Keys** live in `.env` and the gateway only.

Each claim has a code pointer and a test: [ARCHITECTURE.md](../ARCHITECTURE.md) section 10.

## Control mapping

| Framework | Reference | Duty | How Sentry helps |
|---|---|---|---|
| GDPR | Art. 5(1)(c) | Data minimisation | Identifiers (AFM, AMKA, IBAN, names, contact details) are masked before a prompt reaches a cloud model |
| GDPR | Art. 5(1)(f), 32 | Integrity, confidentiality, security of processing | Every prompt is checked before it leaves; restricted documents are blocked; incidents show only pseudonyms and masked previews |
| GDPR | Art. 25 | Data protection by design and default | The safe action is the default (mask or answer locally); policy changes are audited |
| GDPR | Art. 33, 34 | Detect, record and assess breaches | Each blocked, warned or masked event is recorded with time, team and reason |
| GDPR | Chapter V | Limit third-country transfers | Confidential content is answered by the local model |
| NIS2 | Art. 21(2)(a), (e) | Risk analysis, security in using systems | Tool inventory with risk rating, unapproved tools and approved alternatives |
| NIS2 | Art. 21(2)(b), 23 | Incident handling and reporting | Searchable incident log, layers that fired, masked replay, SIEM export |
| NIS2 | Art. 21(2)(i) | Access control, asset management | Per-user keys, pseudonyms, two-person identity reveal |
| EU AI Act | Art. 4 | AI literacy | Plain-word reasons teach people what to do instead |
| EU AI Act | Art. 26(2), 26(5) | Deployer oversight and monitoring | Warn asks a person to confirm; usage per tool and team |
| EU AI Act | Art. 26(6) | Keep automatic logs at least six months (high-risk systems) | Decisions are logged automatically; set `RETENTION_DAYS` for the required period |

## Telling employees

Monitoring staff has legal and works-council implications that vary by country. Before enforcing: publish an AI use policy, tell people what is checked and why, start in shadow mode, and use the "Why this decision" explanation so the tool teaches rather than punishes.

## EU AI Act, plainly

- **Art. 4, AI literacy** applies since 2 February 2025. Plain-word reasons in the product support it.
- **Art. 50, transparency:** main obligations are due in 2026, but secondary sources disagree on whether parts moved to 2 December 2026. **Check EUR-Lex before stating a date to anyone.**
- **High-risk obligations** (Annex III) are reported as moved to 2 December 2027. Sentry is not itself high-risk as designed (it does not decide on people); a customer who uses it to monitor employees should check with counsel.
- Sentry tells people when a message was masked, held or answered by a local model, so nobody unknowingly talks to a stand-in.

Sources (secondary; the Official Journal is the authority): [Kennedys on the AI Act timeline](https://kennedyslaw.com/en/thought-leadership/article/2026/the-eu-ai-act-implementation-timeline-understanding-the-next-deadline-for-compliance), [Future of Privacy Forum on the AI Omnibus](https://fpf.org/?p=250371).

## What we have not done

No data protection impact assessment, no certification, no external audit. No real personal data was ever used; all test data is invented.
