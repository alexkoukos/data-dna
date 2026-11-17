# Fine-tune data for the D7 judge

Made by `scripts/gen_finetune.py` (seed 42) from the invented company in `data/train_org/`. Nothing here comes from `data/org`, `data/documents` or `data/eval`; the script fails if it finds an overlap.

- Examples: **1513** (train 1286, val 227); generated 1390 before balancing, 12 near-duplicates dropped
- YES **454** (30.0%), NO **1059** (70.0%); target 30 / 70
- Hard negatives (same-topic, public, look-alike words, numbers that are not salaries): **1059** = 70.0% of all examples (rule: at least 50%)
- Greek prompts: **699** = 46.2% (rule: at least 40%)
- Highest word-overlap (Jaccard, 3-word shingles) between a validation prompt and a training prompt on the same candidate: 0.76

### By candidate type

| value | YES | NO | train | val | total |
|---|---|---|---|---|---|
| doc_chunk | 352 | 844 | 1018 | 178 | 1196 |
| entity | 102 | 215 | 268 | 49 | 317 |

### By language of the prompt

| value | YES | NO | train | val | total |
|---|---|---|---|---|---|
| el | 220 | 479 | 598 | 101 | 699 |
| en | 234 | 580 | 688 | 126 | 814 |

### By rewrite (label-preserving augmentation)

| value | YES | NO | train | val | total |
|---|---|---|---|---|---|
| greeklish | 13 | 23 | 29 | 7 | 36 |
| noaccent | 14 | 31 | 39 | 6 | 45 |
| none | 363 | 847 | 1029 | 181 | 1210 |
| typo | 24 | 64 | 74 | 14 | 88 |
| upper | 40 | 94 | 115 | 19 | 134 |

### By kind of example

| value | YES | NO | train | val | total |
|---|---|---|---|---|---|
| client_lookalike | 0 | 7 | 5 | 2 | 7 |
| client_lookalike+upper | 0 | 1 | 1 | 0 | 1 |
| client_name | 6 | 0 | 6 | 0 | 6 |
| client_name+upper | 1 | 0 | 1 | 0 | 1 |
| fictional_numbers | 0 | 12 | 11 | 1 | 12 |
| fictional_numbers+typo | 0 | 1 | 1 | 0 | 1 |
| generic_or_public | 0 | 134 | 112 | 22 | 134 |
| generic_or_public+greeklish | 0 | 3 | 2 | 1 | 3 |
| generic_or_public+noaccent | 0 | 6 | 6 | 0 | 6 |
| generic_or_public+typo | 0 | 15 | 11 | 4 | 15 |
| generic_or_public+upper | 0 | 10 | 9 | 1 | 10 |
| indirect_question | 7 | 0 | 5 | 2 | 7 |
| lookalike_word | 0 | 69 | 56 | 13 | 69 |
| lookalike_word+greeklish | 0 | 2 | 2 | 0 | 2 |
| lookalike_word+noaccent | 0 | 3 | 3 | 0 | 3 |
| lookalike_word+upper | 0 | 15 | 11 | 4 | 15 |
| name_el_sentence | 12 | 0 | 11 | 1 | 12 |
| name_el_sentence+greeklish | 1 | 0 | 0 | 1 | 1 |
| name_el_sentence+noaccent | 1 | 0 | 1 | 0 | 1 |
| name_el_sentence+upper | 1 | 0 | 1 | 0 | 1 |
| name_en_sentence | 13 | 0 | 10 | 3 | 13 |
| name_en_sentence+greeklish | 1 | 0 | 1 | 0 | 1 |
| name_en_sentence+noaccent | 1 | 0 | 1 | 0 | 1 |
| name_en_sentence+upper | 3 | 0 | 2 | 1 | 3 |
| number_not_salary | 0 | 70 | 63 | 7 | 70 |
| number_not_salary+greeklish | 0 | 3 | 2 | 1 | 3 |
| number_not_salary+noaccent | 0 | 3 | 3 | 0 | 3 |
| number_not_salary+upper | 0 | 5 | 4 | 1 | 5 |
| paraphrase_cross | 70 | 0 | 58 | 12 | 70 |
| paraphrase_cross+greeklish | 1 | 0 | 1 | 0 | 1 |
| paraphrase_cross+noaccent | 2 | 0 | 2 | 0 | 2 |
| paraphrase_cross+typo | 3 | 0 | 1 | 2 | 3 |
| paraphrase_cross+upper | 6 | 0 | 5 | 1 | 6 |
| paraphrase_same | 70 | 0 | 63 | 7 | 70 |
| paraphrase_same+greeklish | 4 | 0 | 2 | 2 | 4 |
| paraphrase_same+noaccent | 1 | 0 | 1 | 0 | 1 |
| paraphrase_same+typo | 7 | 0 | 7 | 0 | 7 |
| paraphrase_same+upper | 4 | 0 | 3 | 1 | 4 |
| partial_copy | 104 | 0 | 86 | 18 | 104 |
| partial_copy+noaccent | 7 | 0 | 6 | 1 | 7 |
| partial_copy+typo | 12 | 0 | 11 | 1 | 12 |
| partial_copy+upper | 14 | 0 | 14 | 0 | 14 |
| phone | 8 | 0 | 7 | 1 | 8 |
| phone+greeklish | 2 | 0 | 1 | 1 | 2 |
| phone+upper | 2 | 0 | 2 | 0 | 2 |
| public_doc | 0 | 26 | 23 | 3 | 26 |
| public_doc+greeklish | 0 | 1 | 1 | 0 | 1 |
| public_doc+noaccent | 0 | 2 | 2 | 0 | 2 |
| public_doc+typo | 0 | 3 | 2 | 1 | 3 |
| public_doc+upper | 0 | 2 | 2 | 0 | 2 |
| public_figure | 0 | 18 | 14 | 4 | 18 |
| public_figure+upper | 0 | 2 | 2 | 0 | 2 |
| reference_number | 0 | 16 | 15 | 1 | 16 |
| reference_number+greeklish | 0 | 1 | 1 | 0 | 1 |
| salary_figure | 20 | 0 | 16 | 4 | 20 |
| salary_figure+greeklish | 1 | 0 | 1 | 0 | 1 |
| salary_figure+noaccent | 1 | 0 | 1 | 0 | 1 |
| salary_figure+upper | 4 | 0 | 3 | 1 | 4 |
| same_topic_safe | 0 | 495 | 421 | 74 | 495 |
| same_topic_safe+greeklish | 0 | 13 | 12 | 1 | 13 |
| same_topic_safe+noaccent | 0 | 17 | 13 | 4 | 17 |
| same_topic_safe+typo | 0 | 45 | 39 | 6 | 45 |
| same_topic_safe+upper | 0 | 59 | 51 | 8 | 59 |
| summary_numbers | 35 | 0 | 31 | 4 | 35 |
| summary_numbers+greeklish | 1 | 0 | 1 | 0 | 1 |
| summary_numbers+typo | 2 | 0 | 2 | 0 | 2 |
| summary_numbers+upper | 2 | 0 | 1 | 1 | 2 |
| surname_only | 18 | 0 | 16 | 2 | 18 |
| surname_only+greeklish | 2 | 0 | 2 | 0 | 2 |
| surname_only+noaccent | 1 | 0 | 0 | 1 | 1 |
| surname_only+upper | 3 | 0 | 3 | 0 | 3 |

### By source document or entity category

| value | YES | NO | train | val | total |
|---|---|---|---|---|---|
| AMOUNT | 26 | 81 | 93 | 14 | 107 |
| CLIENT | 7 | 8 | 13 | 2 | 15 |
| PERSON | 57 | 109 | 136 | 30 | 166 |
| PHONE | 12 | 17 | 26 | 3 | 29 |
| board | 52 | 117 | 155 | 14 | 169 |
| hr | 49 | 130 | 148 | 31 | 179 |
| nord | 55 | 109 | 130 | 34 | 164 |
| plist | 48 | 131 | 146 | 33 | 179 |
| price | 44 | 100 | 130 | 14 | 144 |
| pub | 0 | 34 | 30 | 4 | 34 |
| sal | 51 | 106 | 130 | 27 | 157 |
| strat | 53 | 117 | 149 | 21 | 170 |

Hard negatives by kind: client_lookalike 7, client_lookalike+upper 1, fictional_numbers 12, fictional_numbers+typo 1, generic_or_public 134, generic_or_public+greeklish 3, generic_or_public+noaccent 6, generic_or_public+typo 15, generic_or_public+upper 10, lookalike_word 69, lookalike_word+greeklish 2, lookalike_word+noaccent 3, lookalike_word+upper 15, number_not_salary 70, number_not_salary+greeklish 3, number_not_salary+noaccent 3, number_not_salary+upper 5, public_doc 26, public_doc+greeklish 1, public_doc+noaccent 2, public_doc+typo 3, public_doc+upper 2, public_figure 18, public_figure+upper 2, reference_number 16, reference_number+greeklish 1, same_topic_safe 495, same_topic_safe+greeklish 13, same_topic_safe+noaccent 17, same_topic_safe+typo 45, same_topic_safe+upper 59

## Format

Each line of `train.jsonl` / `val.jsonl` has `messages` (user turn = instruction + PROMPT + CANDIDATE, assistant turn = the JSON; the Gemma template maps `assistant` to its `model` turn), `text` (the same in native Gemma markers, for trainers that take one column) and `meta` (kind, language, hard flag; drop it before training).
