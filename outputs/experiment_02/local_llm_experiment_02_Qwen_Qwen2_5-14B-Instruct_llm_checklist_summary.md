# Local LLM Experiment 2 Summary

| Model | Architecture | Variant | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | original | 0.786 | 0.789 | 0.857 | 0.822 | 8 | 5 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | paraphrase | 0.843 | 0.865 | 0.914 | 0.889 | 5 | 3 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | subtle | 0.727 | 0.778 | 0.800 | 0.789 | 8 | 7 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | asr_noise | 0.755 | 0.824 | 0.875 | 0.848 | 6 | 4 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | all_augmented | 0.782 | 0.822 | 0.863 | 0.842 | 19 | 14 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | all_variants | 0.783 | 0.814 | 0.861 | 0.837 | 27 | 19 |
