---
description: Help a teammate add prompts, AI tools or org data without breaking anything
argument-hint: "<prompts | tools | org>"
---
Help the user add $ARGUMENTS data. They may not be technical: speak simple Greek and do the file editing for them.

- prompts: add rows to `data/eval/prompts.csv` (columns and allowed values are in `scripts/validate_data.py`). Ask for the text and what the system should do; fill the other columns yourself and confirm with the user. All data fictional.
- tools: add rows to `data/ai_tools.csv`.
- org: edit `data/org/org.yaml`.

Then run `make validate`, fix any problem, and follow the end-of-session rules in `CLAUDE.md` (branch, commit, PR link).
