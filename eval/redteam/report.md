# Red team report

## promptfoo: curated cases (decision must match)

| Category | Passed | Failed |
| --- | --- | --- |
| clean | 6 | 0 |
| document | 3 | 0 |
| evasion | 2 | 0 |
| injection | 7 | 0 |
| pii | 3 | 0 |
| secret | 4 | 0 |

## garak: known attack prompts sent to the safety check

| Prompt family | Prompts | Flagged by the gateway | Share |
| --- | --- | --- | --- |
| promptinject | 40 | 34 | 85% |
| dan | 40 | 29 | 72% |
| encoding | 40 | 5 | 12% |
| latentinjection | 40 | 20 | 50% |
| goodside | 27 | 4 | 15% |

Most garak prompts attack the model's behaviour (jailbreaks, hidden instructions) rather than carry company data, so the gateway is only expected to catch the ones with recognisable injection phrases, secrets or identifiers. The rest reach the model, which is why the approved model should be hardened separately.
