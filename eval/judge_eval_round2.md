# Judge evaluation (D7)

Test set: 639 rows (304 leaks, 335 negatives, 60 of them the original D7 negatives). Test data only; none of it is in the training set.

| model | precision | recall | precision at 30% leaks | false positives on the original 60 | all false positives | unparsed | JSON and reason ok | seconds |
|---|---|---|---|---|---|---|---|---|
| dna-judge2 | 98% | 91% | 96% | **0 of 60** | 5 of 335 | 0 | 100% | 1573 |

### By candidate type (recall on leaks / false positive rate on negatives)

| model | doc_chunk | entity |
|---|---|---|
| dna-judge2 | recall 96% / FP 2% | recall 78% / FP 0% |

### By source (correct / rows)

| source | dna-judge2 |
|---|---|
| aegean_attacks | 20/20 |
| aegean_holdout | 30/30 |
| aegean_prompts | 121/127 |
| akryon_prompts | 136/147 |
| akryon_public | 32/32 |
| aug | 102/107 |
| entity_new | 79/89 |
| gold_new | 86/87 |

### By slice (correct / rows; for a YES slice that is recall, for a NO slice it is 1 minus the false positive rate)

| slice | kind | dna-judge2 |
|---|---|---|
| aug_greeklish | mixed | 9/11 |
| aug_noaccent | mixed | 19/20 |
| aug_typo | mixed | 29/30 |
| aug_upper | mixed | 45/46 |
| clean | NO | 58/58 |
| client_name | YES | 8/12 |
| client_name_prompt | YES | 6/7 |
| copy | YES | 20/22 |
| copy_exact | YES | 1/1 |
| edit | YES | 25/25 |
| email_prompt | YES | 4/6 |
| fictional_numbers | NO | 4/4 |
| general | NO | 44/46 |
| generic | NO | 1/1 |
| indirect_question | YES | 3/3 |
| lookalike_word | NO | 18/18 |
| number_not_salary | NO | 16/16 |
| numbers_only | YES | 1/1 |
| paraphrase | YES | 87/89 |
| paraphrase_cross | YES | 12/12 |
| paraphrase_same | YES | 13/13 |
| person_full_name | YES | 11/12 |
| person_prompt | YES | 1/1 |
| person_surname_only | YES | 11/12 |
| phone_prompt | YES | 0/3 |
| public_doc | NO | 6/6 |
| public_doc_copy | NO | 32/32 |
| public_fact | NO | 7/8 |
| public_figure | NO | 7/7 |
| salary_figure | YES | 8/12 |
| same_topic | NO | 75/76 |
| split | YES | 12/16 |
| summary_numbers | YES | 6/6 |
| trap | NO | 3/3 |
| trap_same_number | NO | 1/1 |
| trap_similar_words | NO | 3/3 |

Precision and recall are over all rows. An answer that is not valid JSON counts as NO. 'Precision at 30% leaks' re-weights the false positive rate to the real base rate. Reference: untuned gemma3:1b gave 42 false positives out of the 60 (earlier prompt, so not exactly comparable).
