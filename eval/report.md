# Data DNA evaluation report

Prompt set: `prompts.csv` (195 prompts).

## Targets (PRD section 17)

| Metric | Target | Result | Status |
| --- | --- | --- | --- |
| Recall, paraphrased document leaks | >= 80% | 100.0 | PASS |
| False alarms on clean prompts | <= 5% | 2.1 | PASS |
| Added latency p95 | < 100 ms | 67.4 | PASS |
| Prompts with zero LLM tokens | >= 90% | 100.0 | PASS |
| Correct copy named (leaks with 3 or more marks) | >= 90% | 99.2 | PASS |
| Greeklish, look-alike and foreign-digit attacks caught (X5) | >= 80% | 100.0 | PASS |
| Decoy credentials raise the alarm (X4) | 100% | 100.0 | PASS |
| False alarms on clean look-alikes (X2) | <= 5% | 0.0 | PASS |

## Detection by leak type (recall, with the regex-and-keyword baseline)

| Leak type | Prompts | Recall % | Baseline recall % |
| --- | --- | --- | --- |
| copy | 12 | 100.0 | 0.0 |
| edit | 15 | 100.0 | 6.7 |
| paraphrase | 40 | 100.0 | 5.0 |
| pattern | 50 | 100.0 | 74.0 |
| split | 6 | 100.0 | 16.7 |

## By language

| Language | Leaks | Recall % | Clean | False alarms % |
| --- | --- | --- | --- | --- |
| el | 44 | 100.0 | 18 | 5.6 |
| en | 79 | 100.0 | 30 | 0.0 |

## Other measures

- Paraphrases flagged by any check, including luck such as a client name: 100.0%
- Decision matches the label's expected decision: 93.8%
- Prompt injection caught: 100.0%
- Evasion attempts caught: 100.0%
- False alarms, baseline: 2.1%
- Latency p50 / p95: 19.4 / 67.4 ms (no LLM judge)
- Zero-LLM share: 100.0%, LLM tokens used: 0

## Where the decision differs from the label

| Id | Type | Expected | Got | Text |
| --- | --- | --- | --- | --- |
| P0050 | pattern | warn | mask | Γράψε ένα email στην Olympos Retail για την καθυστέρηση της παράδοσης. |
| P0078 | paraphrase | local | block | We want to set up shop in Sofia and Belgrade around April to June 2027 and the budget is r |
| P0079 | paraphrase | local | block | The Bulgarian plan is to buy a little Sofia consultancy named Danube Advisory for about 1. |
| P0080 | paraphrase | local | block | In Serbia we simply lease space in Belgrade, find a country manager before the end of Marc |
| P0082 | paraphrase | local | block | Nobody beyond the executive committee should talk about the Danube deal, the money or the  |
| P0083 | paraphrase | local | block | The exclusivity we got from the Danube sellers expires on 15 April, so the board has to de |
| P0084 | paraphrase | local | block | If it passes, staff hear about the expansion in the first week of May and the Sofia office |
| P0085 | paraphrase | local | block | Can you turn this into a slide: ask the board to approve a four million euro budget, an ac |
| P0086 | paraphrase | local | block | Η διοίκηση προτείνει να ανοίξουμε γραφεία στη Σόφια και στο Βελιγράδι το δεύτερο τρίμηνο τ |
| P0090 | paraphrase | local | block | Summarise in bullets: two new offices (Sofia and Belgrade) in Q2 2027, 4 million euro budg |
| P0159 | clean | allow | local | Βοήθησέ με να υπολογίσω ένα ποσοστό αύξησης σε ένα λογιστικό φύλλο. |
| P0194 | pattern | mask | warn | Card number: 4949-0668-8281-1265 |

## Attack set (data/eval/attacks.csv)

80 of 80 attacks handled as expected (100.0%).

| Technique | Handled | Of |
| --- | --- | --- |
| invisible_chars | 4 | 4 |
| spaced | 6 | 6 |
| homoglyph | 10 | 10 |
| encoding | 10 | 10 |
| injection | 15 | 15 |
| document_rewrite | 10 | 10 |
| secret | 10 | 10 |
| clean | 10 | 10 |
| combined | 5 | 5 |

## Script and decoy attacks: data/eval/attacks_scripts.csv (X4, X5)

80 attacks. Caught (any action but allow): 100.0%. Exact decision as expected: 100.0%. False alarms on the clean look-alikes: 0.0%.

| Kind | Attacks | Caught % | Decision as expected % |
| --- | --- | --- | --- |
| clean_lookalike | 8 | false alarms 0.0 | 100.0 |
| documents | 8 | 100.0 | 100.0 |
| encoding | 8 | 100.0 | 100.0 |
| greeklish | 10 | 100.0 | 100.0 |
| honeytoken | 4 | 100.0 | 100.0 |
| injection | 8 | 100.0 | 100.0 |
| look_alike | 10 | 100.0 | 100.0 |
| other_digits | 6 | 100.0 | 100.0 |
| secrets | 8 | 100.0 | 100.0 |
| spacing | 10 | 100.0 | 100.0 |

Attacks whose outcome differs from the expectation (known gaps stay on purpose):

None.
