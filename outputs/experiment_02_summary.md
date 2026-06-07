# Experiment 2 Summary

| Model | Variant | Accuracy | Recall fraud | FP | FN |
|---|---|---:|---:|---:|---:|
| llm_checklist | original | 0.400 | 0.462 | 0 | 14 |
| llm_checklist | paraphrase | 0.429 | 0.550 | 1 | 9 |
| llm_checklist | subtle | 0.344 | 0.300 | 0 | 14 |
| llm_checklist | asr_noise | 0.571 | 0.667 | 0 | 1 |
| llm_self_check | original | 0.400 | 0.462 | 0 | 14 |
| llm_self_check | paraphrase | 0.429 | 0.550 | 1 | 9 |
| llm_self_check | subtle | 0.344 | 0.300 | 0 | 14 |
| llm_self_check | asr_noise | 0.571 | 0.667 | 0 | 1 |
| llm_ensemble | original | 0.400 | 0.462 | 0 | 14 |
| llm_ensemble | paraphrase | 0.429 | 0.550 | 1 | 9 |
| llm_ensemble | subtle | 0.344 | 0.300 | 0 | 14 |
| llm_ensemble | asr_noise | 0.571 | 0.667 | 0 | 1 |
