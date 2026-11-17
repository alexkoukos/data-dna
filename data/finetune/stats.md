# Fine-tune data for the D7 judge

Made by `scripts/gen_finetune.py` (seed 42) from the invented company in `data/train_org/`. Nothing here comes from `data/org`, `data/documents` or `data/eval`; the script fails if it finds an overlap.

- Examples: **1932** (train 1643, val 289); generated 1733 before balancing, 46 near-duplicates dropped
- YES **571** (29.6%), NO **1361** (70.4%); target 30 / 70
- Hard negatives (same-topic, public, look-alike words, numbers that are not salaries): **1361** = 70.4% of all examples (rule: at least 50%)
- Greek prompts: **857** = 44.4% (rule: at least 40%)
- Highest word-overlap (Jaccard, 3-word shingles) between a validation prompt and a training prompt on the same candidate: 0.75

### By candidate type

| value | YES | NO | train | val | total |
|---|---|---|---|---|---|
| doc_chunk | 425 | 1023 | 1229 | 219 | 1448 |
| entity | 146 | 338 | 414 | 70 | 484 |

### By language of the prompt

| value | YES | NO | train | val | total |
|---|---|---|---|---|---|
| el | 270 | 587 | 726 | 131 | 857 |
| en | 301 | 774 | 917 | 158 | 1075 |

### By rewrite (label-preserving augmentation)

| value | YES | NO | train | val | total |
|---|---|---|---|---|---|
| greeklish | 22 | 33 | 49 | 6 | 55 |
| noaccent | 8 | 32 | 34 | 6 | 40 |
| none | 457 | 1066 | 1294 | 229 | 1523 |
| typo | 32 | 86 | 101 | 17 | 118 |
| upper | 52 | 144 | 165 | 31 | 196 |

### By kind of example

| value | YES | NO | train | val | total |
|---|---|---|---|---|---|
| client_lookalike | 0 | 15 | 11 | 4 | 15 |
| client_lookalike+upper | 0 | 3 | 2 | 1 | 3 |
| client_name | 46 | 0 | 41 | 5 | 46 |
| client_name+greeklish | 3 | 0 | 3 | 0 | 3 |
| client_name+noaccent | 1 | 0 | 1 | 0 | 1 |
| client_name+upper | 10 | 0 | 10 | 0 | 10 |
| fictional_numbers | 0 | 14 | 12 | 2 | 14 |
| fictional_numbers+greeklish | 0 | 1 | 1 | 0 | 1 |
| fictional_numbers+upper | 0 | 3 | 2 | 1 | 3 |
| fragment_copy | 62 | 0 | 53 | 9 | 62 |
| fragment_copy+greeklish | 1 | 0 | 1 | 0 | 1 |
| fragment_copy+noaccent | 2 | 0 | 1 | 1 | 2 |
| fragment_copy+typo | 5 | 0 | 3 | 2 | 5 |
| fragment_copy+upper | 5 | 0 | 5 | 0 | 5 |
| generic_or_public | 0 | 204 | 180 | 24 | 204 |
| generic_or_public+greeklish | 0 | 4 | 2 | 2 | 4 |
| generic_or_public+noaccent | 0 | 5 | 4 | 1 | 5 |
| generic_or_public+typo | 0 | 16 | 14 | 2 | 16 |
| generic_or_public+upper | 0 | 21 | 19 | 2 | 21 |
| indirect_question | 7 | 0 | 7 | 0 | 7 |
| indirect_question+greeklish | 1 | 0 | 1 | 0 | 1 |
| lookalike_word | 0 | 81 | 75 | 6 | 81 |
| lookalike_word+greeklish | 0 | 2 | 1 | 1 | 2 |
| lookalike_word+noaccent | 0 | 4 | 3 | 1 | 4 |
| lookalike_word+upper | 0 | 18 | 18 | 0 | 18 |
| name_el_sentence | 11 | 0 | 9 | 2 | 11 |
| name_el_sentence+greeklish | 1 | 0 | 1 | 0 | 1 |
| name_el_sentence+upper | 1 | 0 | 0 | 1 | 1 |
| name_en_sentence | 8 | 0 | 6 | 2 | 8 |
| name_en_sentence+greeklish | 1 | 0 | 1 | 0 | 1 |
| number_not_salary | 0 | 116 | 95 | 21 | 116 |
| number_not_salary+greeklish | 0 | 5 | 5 | 0 | 5 |
| number_not_salary+noaccent | 0 | 2 | 2 | 0 | 2 |
| number_not_salary+upper | 0 | 28 | 25 | 3 | 28 |
| paraphrase_cross | 70 | 0 | 53 | 17 | 70 |
| paraphrase_cross+greeklish | 2 | 0 | 1 | 1 | 2 |
| paraphrase_cross+noaccent | 3 | 0 | 3 | 0 | 3 |
| paraphrase_cross+typo | 10 | 0 | 9 | 1 | 10 |
| paraphrase_cross+upper | 5 | 0 | 5 | 0 | 5 |
| paraphrase_same | 70 | 0 | 65 | 5 | 70 |
| paraphrase_same+greeklish | 2 | 0 | 2 | 0 | 2 |
| paraphrase_same+typo | 9 | 0 | 9 | 0 | 9 |
| paraphrase_same+upper | 9 | 0 | 6 | 3 | 9 |
| partial_copy | 99 | 0 | 83 | 16 | 99 |
| partial_copy+greeklish | 4 | 0 | 4 | 0 | 4 |
| partial_copy+noaccent | 2 | 0 | 2 | 0 | 2 |
| partial_copy+typo | 6 | 0 | 4 | 2 | 6 |
| partial_copy+upper | 11 | 0 | 9 | 2 | 11 |
| public_doc | 0 | 59 | 52 | 7 | 59 |
| public_doc+greeklish | 0 | 7 | 7 | 0 | 7 |
| public_doc+noaccent | 0 | 4 | 4 | 0 | 4 |
| public_doc+typo | 0 | 9 | 8 | 1 | 9 |
| public_doc+upper | 0 | 25 | 20 | 5 | 25 |
| public_figure | 0 | 28 | 25 | 3 | 28 |
| public_figure+greeklish | 0 | 1 | 1 | 0 | 1 |
| public_figure+noaccent | 0 | 1 | 1 | 0 | 1 |
| public_figure+upper | 0 | 3 | 3 | 0 | 3 |
| reference_number | 0 | 26 | 20 | 6 | 26 |
| reference_number+noaccent | 0 | 1 | 1 | 0 | 1 |
| reference_number+upper | 0 | 4 | 2 | 2 | 4 |
| salary_figure | 7 | 0 | 5 | 2 | 7 |
| salary_figure+upper | 2 | 0 | 1 | 1 | 2 |
| same_topic_safe | 0 | 523 | 436 | 87 | 523 |
| same_topic_safe+greeklish | 0 | 13 | 12 | 1 | 13 |
| same_topic_safe+noaccent | 0 | 15 | 12 | 3 | 15 |
| same_topic_safe+typo | 0 | 61 | 52 | 9 | 61 |
| same_topic_safe+upper | 0 | 39 | 31 | 8 | 39 |
| summary_numbers | 35 | 0 | 30 | 5 | 35 |
| summary_numbers+greeklish | 2 | 0 | 2 | 0 | 2 |
| summary_numbers+typo | 2 | 0 | 2 | 0 | 2 |
| summary_numbers+upper | 1 | 0 | 1 | 0 | 1 |
| surname_only | 42 | 0 | 36 | 6 | 42 |
| surname_only+greeklish | 5 | 0 | 4 | 1 | 5 |
| surname_only+upper | 8 | 0 | 6 | 2 | 8 |

### By source document or entity category

| value | YES | NO | train | val | total |
|---|---|---|---|---|---|
| AMOUNT | 9 | 151 | 133 | 27 | 160 |
| CLIENT | 60 | 18 | 68 | 10 | 78 |
| PERSON | 77 | 138 | 190 | 25 | 215 |
| PHONE | 0 | 31 | 23 | 8 | 31 |
| board | 64 | 128 | 165 | 27 | 192 |
| hr | 61 | 142 | 171 | 32 | 203 |
| nord | 66 | 123 | 152 | 37 | 189 |
| plist | 58 | 160 | 170 | 48 | 218 |
| price | 54 | 110 | 148 | 16 | 164 |
| pub | 0 | 51 | 45 | 6 | 51 |
| pub2 | 0 | 53 | 46 | 7 | 53 |
| sal | 60 | 123 | 163 | 20 | 183 |
| strat | 62 | 133 | 169 | 26 | 195 |

Hard negatives by kind: client_lookalike 15, client_lookalike+upper 3, fictional_numbers 14, fictional_numbers+greeklish 1, fictional_numbers+upper 3, generic_or_public 204, generic_or_public+greeklish 4, generic_or_public+noaccent 5, generic_or_public+typo 16, generic_or_public+upper 21, lookalike_word 81, lookalike_word+greeklish 2, lookalike_word+noaccent 4, lookalike_word+upper 18, number_not_salary 116, number_not_salary+greeklish 5, number_not_salary+noaccent 2, number_not_salary+upper 28, public_doc 59, public_doc+greeklish 7, public_doc+noaccent 4, public_doc+typo 9, public_doc+upper 25, public_figure 28, public_figure+greeklish 1, public_figure+noaccent 1, public_figure+upper 3, reference_number 26, reference_number+noaccent 1, reference_number+upper 4, same_topic_safe 523, same_topic_safe+greeklish 13, same_topic_safe+noaccent 15, same_topic_safe+typo 61, same_topic_safe+upper 39

## Format

Each line of `train.jsonl` / `val.jsonl` has `messages` (user turn = instruction + PROMPT + CANDIDATE, assistant turn = the JSON; the Gemma template maps `assistant` to its `model` turn), `text` (the same in native Gemma markers, for trainers that take one column) and `meta` (kind, language, hard flag; drop it before training).
