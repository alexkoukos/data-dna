# Privacy, GDPR and the EU AI Act (T5)

One page. It describes what the product does; it is not legal advice and certifies nothing. A lawyer or DPO should confirm how each duty applies. The article-by-article table is in `compliance-mapping.md` and in the one-click PDF.

## A watcher must be careful with what it watches
A tool that reads every prompt is itself a privacy risk, so we limit what it keeps:
- **Less data.** Detection runs first and sensitive values are masked before a prompt goes to a cloud model. Incidents store entity names, categories and masked previews, not the prompt (GDPR Art. 5(1)(c), data minimisation).
- **Fingerprints, not text** for registered documents.
- **Names stay sealed.** Incidents show a pseudonym. A real name appears only after one person asks with a reason and a different person approves; each step is in the audit log (Art. 5(1)(f), 32, 25).
- **Deletion.** Records are purged after `RETENTION_DAYS` (default 30), also on demand.
- **Local by default for confidential content.** The local model answers, so the text does not leave the company (Chapter V transfers).
- **Split storage for the most sensitive fields.** Values are split into two shares in two separate databases with integrity tags, so a dump of one store reveals nothing and tampering is detected. See README "Split storage".
- **Keys.** API keys live in `.env` and the gateway only; the integrity key is a compose secret never stored in the vaults.

## Telling employees
Monitoring staff has legal and works-council implications that vary by country. Before enforcing: publish an AI use policy, tell people what is checked and why, start in shadow mode, and use the "Why?" explanation so the tool teaches rather than punishes. This also supports the AI literacy duty below.

## EU AI Act, plainly
- **Art. 4, AI literacy:** applies since 2 February 2025; organisations must take measures so staff using AI understand it. Plain-word reasons in the product support this. The wording was amended by the Digital Omnibus; the date did not change.
- **Art. 50, transparency:** main obligations are due in 2026, but secondary sources disagree on whether parts were postponed to 2 December 2026. **Check EUR-Lex before stating a date to anyone.**
- **High-risk obligations** (Annex III) are reported as moved to 2 December 2027. Pyli is not itself a high-risk system as designed (it does not decide on people); a customer who uses it to monitor employees should check with counsel whether their use changes that.
- Pyli tells people when a message was masked, held or answered by a local model, so the user is never unknowingly talking to a stand-in.

Sources: [Kennedys on the AI Act timeline](https://kennedyslaw.com/en/thought-leadership/article/2026/the-eu-ai-act-implementation-timeline-understanding-the-next-deadline-for-compliance), [Future of Privacy Forum on the AI Omnibus](https://fpf.org/?p=250371). Both are secondary sources; the Official Journal is the authority.

## What we have not done
No data protection impact assessment, no certification, no external audit, and no real personal data was ever used (all test data is invented).
