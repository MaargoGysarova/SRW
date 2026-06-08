# Local LLM Experiment 2 Summary

| Model | Architecture | Variant | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | original | 0.771 | 0.775 | 0.886 | 0.827 | 9 | 4 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | paraphrase | 0.743 | 0.789 | 0.857 | 0.822 | 8 | 5 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | subtle | 0.673 | 0.732 | 0.857 | 0.789 | 11 | 5 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | asr_noise | 0.714 | 0.778 | 0.875 | 0.824 | 8 | 4 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | all_augmented | 0.713 | 0.765 | 0.863 | 0.811 | 27 | 14 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | all_variants | 0.730 | 0.768 | 0.869 | 0.815 | 36 | 18 |
