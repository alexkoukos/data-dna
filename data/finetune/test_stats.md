# Test set for the D7 judge

Made by `scripts/gen_judge_test.py` (seed 4242). **Never trained on**: no 6-word run, document, client or multi-word person name is shared with `train.jsonl` / `val.jsonl` (the script stops otherwise).

- Rows: **639**; YES 304 (48%), NO 335; Greek prompts 280 (44%)
- Original D7 negatives (48 clean + 12 same-topic, the 60 the 42 false positives were measured on): **60** (`d7_neg60`)
- Akryon pack included: **yes**
- Candidates use the nearest chunk by character overlap and a label-neutral score (same distribution for YES and NO)

### By source

| value | YES | NO | total |
|---|---|---|---|
| aegean_attacks | 10 | 10 | 20 |
| aegean_holdout | 18 | 12 | 30 |
| aegean_prompts | 79 | 48 | 127 |
| akryon_prompts | 62 | 85 | 147 |
| akryon_public | 0 | 32 | 32 |
| aug | 51 | 56 | 107 |
| entity_new | 48 | 41 | 89 |
| gold_new | 36 | 51 | 87 |

### By candidate type

| value | YES | NO | total |
|---|---|---|---|
| doc_chunk | 224 | 287 | 511 |
| entity | 80 | 48 | 128 |

### By slice

| value | YES | NO | total |
|---|---|---|---|
| aug_greeklish | 3 | 8 | 11 |
| aug_noaccent | 11 | 9 | 20 |
| aug_typo | 11 | 19 | 30 |
| aug_upper | 26 | 20 | 46 |
| clean | 0 | 58 | 58 |
| client_name | 12 | 0 | 12 |
| client_name_prompt | 7 | 0 | 7 |
| copy | 22 | 0 | 22 |
| copy_exact | 1 | 0 | 1 |
| edit | 25 | 0 | 25 |
| email_prompt | 6 | 0 | 6 |
| fictional_numbers | 0 | 4 | 4 |
| general | 0 | 46 | 46 |
| generic | 0 | 1 | 1 |
| indirect_question | 3 | 0 | 3 |
| lookalike_word | 0 | 18 | 18 |
| number_not_salary | 0 | 16 | 16 |
| numbers_only | 1 | 0 | 1 |
| paraphrase | 89 | 0 | 89 |
| paraphrase_cross | 12 | 0 | 12 |
| paraphrase_same | 13 | 0 | 13 |
| person_full_name | 12 | 0 | 12 |
| person_prompt | 1 | 0 | 1 |
| person_surname_only | 12 | 0 | 12 |
| phone_prompt | 3 | 0 | 3 |
| public_doc | 0 | 6 | 6 |
| public_doc_copy | 0 | 32 | 32 |
| public_fact | 0 | 8 | 8 |
| public_figure | 0 | 7 | 7 |
| salary_figure | 12 | 0 | 12 |
| same_topic | 0 | 76 | 76 |
| split | 16 | 0 | 16 |
| summary_numbers | 6 | 0 | 6 |
| trap | 0 | 3 | 3 |
| trap_same_number | 0 | 1 | 1 |
| trap_similar_words | 0 | 3 | 3 |

### By language of the prompt

| value | YES | NO | total |
|---|---|---|---|
| el | 135 | 145 | 280 |
| en | 169 | 190 | 359 |
