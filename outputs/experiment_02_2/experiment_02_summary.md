# Experiment 2 Summary

| Model | Variant | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|
| rules_baseline | original | 0.471 | 0.833 | 0.571 | 0.678 | 4 | 15 |
| rules_baseline | paraphrase | 0.429 | 0.826 | 0.543 | 0.655 | 4 | 16 |
| rules_baseline | subtle | 0.400 | 0.857 | 0.514 | 0.643 | 3 | 17 |
| rules_baseline | asr_noise | 0.082 | 1.000 | 0.062 | 0.118 | 0 | 30 |
| rules_baseline | all_augmented | 0.322 | 0.848 | 0.382 | 0.527 | 7 | 63 |
| rules_baseline | all_variants | 0.365 | 0.843 | 0.431 | 0.570 | 11 | 78 |
