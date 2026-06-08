# Local LLM Experiment 2 Summary

| Model | Architecture | Variant | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | original | 0.700 | 0.750 | 0.943 | 0.835 | 11 | 2 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | paraphrase | 0.729 | 0.800 | 0.914 | 0.853 | 8 | 3 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | subtle | 0.636 | 0.727 | 0.914 | 0.810 | 12 | 3 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | asr_noise | 0.714 | 0.811 | 0.938 | 0.870 | 7 | 2 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | all_augmented | 0.695 | 0.777 | 0.922 | 0.843 | 27 | 8 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | all_variants | 0.697 | 0.770 | 0.927 | 0.841 | 38 | 10 |
