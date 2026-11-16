# Compliance mapping (X17)

Which duty each Data DNA control helps with. The same table is built into the one-click PDF report (`GET /v1/compliance-report.pdf`, source `services/brain/src/brain/compliance.py`). It supports the company's own compliance work. It is not legal advice and it certifies nothing: a lawyer or data protection officer should confirm how each duty applies.

| Framework | Reference | Duty | How Data DNA helps |
|---|---|---|---|
| GDPR | Art. 5(1)(c) | Data minimisation | Identifiers (AFM, AMKA, IBAN, names, contact details) are masked before a prompt reaches a cloud model |
| GDPR | Art. 5(1)(f), 32 | Integrity, confidentiality, security of processing | Every prompt is checked before it leaves; restricted documents are blocked; incidents show only pseudonyms and masked previews |
| GDPR | Art. 25 | Data protection by design and default | Safe action is the default (mask or answer locally); policy changes are audited |
| GDPR | Art. 33, 34 | Detect, record and assess breaches | Each blocked, warned or masked event is recorded with time, team and reason |
| GDPR | Chapter V | Limit third-country transfers | Confidential content is answered by the local model |
| NIS2 | Art. 21(2)(a), (e) | Risk analysis, security in using systems | Tool inventory with risk rating, unapproved tools and approved alternatives |
| NIS2 | Art. 21(2)(b), 23 | Incident handling and reporting | Searchable incident log, layers that fired, masked replay |
| NIS2 | Art. 21(2)(i) | Access control, asset management | Per-user keys, pseudonyms, two-person identity reveal |
| EU AI Act | Art. 26(2), 26(5) | Deployer human oversight and monitoring | Warn asks a person to confirm; usage per tool and team |
| EU AI Act | Art. 26(6) | Keep automatic logs at least six months (high-risk systems) | Decisions logged automatically; set `RETENTION_DAYS` for the required period |
| EU AI Act | Art. 4 | AI literacy | Plain-word reasons teach people what to do instead |

Open for the business owner (Vasilis): confirm the article references and wording with a lawyer before any customer sees the report.
