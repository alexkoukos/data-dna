# Threat model

What Sentry stops, what it does not, and how sure we are. Written for the judges and for the first customer's security team, so it says the uncomfortable parts too. Numbers come from `make eval`, `make calibrate` and the attack file `data/eval/attacks.csv`; all test data is invented.

## What we protect
Company data leaving through AI tools: personal identifiers (AFM, AMKA, IBAN, cards, ID, phones), secrets and keys, source code, client names, and the text of confidential documents (copied, lightly edited, or paraphrased).

## Who and what we defend against
| Actor | Example | Stopped? |
|---|---|---|
| Careless employee | Pastes a client list into a public chatbot | **Yes**, if the traffic goes through the gateway |
| Employee in a hurry | Pastes a document, changes a few words | **Mostly**: copies and near copies are caught; paraphrases 40 of 40 on our own test set, which we tuned on, so expect less on rewrites nobody has tried (`make eval`; `docs/calibration.md` has the trade-off and the holdout results) |
| Curious employee who tries to trick it | Spaced digits, base64, look-alike letters, Greeklish | **Mostly**: the normaliser undoes the common tricks; the "Try to break it" page lets you test |
| Prompt injection inside a file or tool result | "Ignore previous instructions" in a PDF | **Yes** for known phrasings and the classifier; novel attacks may pass |
| Malicious insider with intent | Retypes a document by hand, photographs the screen | **No** for the typing and the photo. We can only deter: marked copies (DNA) make a leaked copy traceable to its recipient |
| Compromised model provider | The vendor stores prompts | **Reduced**: masked and local answers send less; we do not control the vendor |
| Attacker with network access to the brain | Calls `/v1/policies`, creates keys | **No**: demo mode has no login. Do not expose ports 8001 and 4000 beyond a trusted network |

## Where the controls sit
Cheapest first: normalisation, patterns with checksums, YARA and code fingerprints, people and client names, document matching (MinHash then embeddings), session memory across prompts, injection checks, policy. Every decision stores which layers fired (the "Why?" panel). Output is checked too: secrets and restricted text in a model's answer are withheld.

## What we do not stop (honest limits)
- **Traffic that bypasses the gateway.** Personal devices, mobile data, tools with pinned certificates. Network controls (docs/GATEWAY_SETUP.md) reduce this; nothing removes it.
- **Meaning without matching words.** A paraphrase that shares no wording or topic with the registered documents can pass. A paraphrase of a restricted document that scores below 0.91 goes to the local model rather than being blocked, on purpose, to avoid false blocks; at 0.91 or above on a restricted document it is blocked.
- **Slow leaks.** Session memory reassembles a document across prompts inside a time window; leaking one line a day beyond it is not caught.
- **Images and scans** are read with OCR (RapidOCR, in the brain image): screenshots, photos of text and scanned PDF pages (up to 10 per file). Handwriting, low-quality photos and pictures inside a Word file or a text page of a PDF are missed. Audio and file types the brain cannot read are refused at the gateway, not passed. A file the provider fetches from a web address (an image URL) is not downloaded or checked. Other languages beyond Greek, English, German and French match by exact copy only.
- **Detection is probabilistic.** Expect false alarms (a question about a similar topic goes local) and misses. Shadow mode measures them before enforcement.
- **People data.** Names are found by language models, which miss rare names and flag some common words.
- **Honeytokens only catch what was planted.** They prove a specific document leaked; they do not detect other leaks.
- **Our own surface.** The demo has no login, a default master key and open ports. The identity of an employee behind a pseudonym needs two people to approve, but the brain API itself is unauthenticated in demo mode.

## Privacy by design
Raw prompts are not stored: incidents keep a masked preview, categories and reasons, deleted after `RETENTION_DAYS`. Names are pseudonyms until a two-person reveal, which is audited. The paste guard, the browser extension and the gateway send text only to the company's own brain.

## What would change the picture
A login and roles for the web and the brain API, TLS everywhere, a managed key store, and per-tenant data separation. None of these exist yet, and we do not claim them.
