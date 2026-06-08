# Local LLM Experiment 1 Summary

| Model | Architecture | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-14B-Instruct | single_llm | 0.835 | 0.938 | 0.857 | 0.896 | 2 | 5 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | 0.824 | 0.789 | 0.857 | 0.822 | 8 | 5 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | 0.753 | 0.750 | 0.943 | 0.835 | 11 | 2 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | 0.812 | 0.775 | 0.886 | 0.827 | 9 | 4 |
