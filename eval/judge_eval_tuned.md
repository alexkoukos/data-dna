# Judge evaluation (D7)

Test set: 639 rows (304 leaks, 335 negatives, 60 of them the original D7 negatives). Test data only; none of it is in the training set.

| model | precision | recall | precision at 30% leaks | false positives on the original 60 | all false positives | unparsed | JSON and reason ok | seconds |
|---|---|---|---|---|---|---|---|---|
| dna-judge | 96% | 91% | 92% | **1 of 60** | 12 of 335 | 1 | 100% | 1768 |

### By candidate type (recall on leaks / false positive rate on negatives)

| model | doc_chunk | entity |
|---|---|---|
| dna-judge | recall 96% / FP 3% | recall 78% / FP 4% |

### By source (correct / rows)

| source | dna-judge |
|---|---|
| aegean_attacks | 20/20 |
| aegean_holdout | 29/30 |
| aegean_prompts | 124/127 |
| akryon_prompts | 134/147 |
| akryon_public | 31/32 |
| aug | 99/107 |
| entity_new | 76/89 |
| gold_new | 86/87 |

### By slice (correct / rows; for a YES slice that is recall, for a NO slice it is 1 minus the false positive rate)

| slice | kind | dna-judge |
|---|---|---|
| aug_greeklish | mixed | 9/11 |
| aug_noaccent | mixed | 19/20 |
| aug_typo | mixed | 27/30 |
| aug_upper | mixed | 44/46 |
| clean | NO | 57/58 |
| client_name | YES | 3/12 |
| client_name_prompt | YES | 3/7 |
| copy | YES | 20/22 |
| copy_exact | YES | 1/1 |
| edit | YES | 25/25 |
| email_prompt | YES | 5/6 |
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
| person_surname_only | YES | 10/12 |
| phone_prompt | YES | 3/3 |
| public_doc | NO | 5/6 |
| public_doc_copy | NO | 31/32 |
| public_fact | NO | 7/8 |
| public_figure | NO | 6/7 |
| salary_figure | YES | 12/12 |
| same_topic | NO | 75/76 |
| split | YES | 13/16 |
| summary_numbers | YES | 6/6 |
| trap | NO | 3/3 |
| trap_same_number | NO | 1/1 |
| trap_similar_words | NO | 3/3 |

Precision and recall are over all rows. An answer that is not valid JSON counts as NO. 'Precision at 30% leaks' re-weights the false positive rate to the real base rate. Reference from PROGRESS.md: untuned gemma3:1b gave 42 false positives out of the 60 (earlier prompt, so not exactly comparable).
