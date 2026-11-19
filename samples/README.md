# Sample prompts

One ready-to-paste text for each of the five outcomes, in English (`en/`) and Greek (`el/`). Every name, number and amount is invented.

| File | What it shows | Expected outcome |
|---|---|---|
| `1-allow.txt` | An ordinary work question | **Allowed**: nothing happens, no friction |
| `2-mask.txt` | A tax number and an IBAN | **Masked**: replaced by `[AFM_1]` and `[IBAN_1]` before sending; the answer shows the real values again, on your page only |
| `3-warn.txt` | A client name | **Check first**: a card asks you to confirm and say why |
| `4-redirect.txt` | Salary bands from a confidential document, rewritten (English) or copied (Greek) | **Company AI**: the card offers to answer it with the company's own model |
| `5-block.txt` | The board memo about an acquisition | **Blocked**: it was not sent, with the reason and what to do instead |

Paste each into the demo chat at http://localhost:3100 with the extension loaded. The dashboard's "Get the extension" page shows the same texts with a copy button.

Outcomes 4 and 5 compare your text with the registered documents in `data/documents/`, so they need the full stack (`docker compose up --build`). Outcomes 1 to 3 also work with the extension alone: it checks in the browser first (see the README).
