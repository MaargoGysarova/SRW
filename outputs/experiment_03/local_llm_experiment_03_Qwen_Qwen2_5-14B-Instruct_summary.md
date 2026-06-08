# Local LLM Experiment 3 Summary

| Model | Architecture | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-14B-Instruct | single_llm | 0.852 | 1.000 | 0.967 | 0.983 | 0 | 1 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | 0.885 | 1.000 | 0.933 | 0.966 | 0 | 2 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | 0.967 | 1.000 | 0.967 | 0.983 | 0 | 1 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | 0.934 | 1.000 | 0.967 | 0.983 | 0 | 1 |
