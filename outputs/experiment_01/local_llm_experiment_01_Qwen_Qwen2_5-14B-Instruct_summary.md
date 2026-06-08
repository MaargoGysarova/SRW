# Local LLM Experiment 1 Summary

| Model | Architecture | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |
|---|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-14B-Instruct | single_llm | 0.835 | 0.938 | 0.857 | 0.896 | 2 | 5 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | 0.729 | 1.000 | 0.514 | 0.679 | 0 | 17 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | 0.494 | 1.000 | 0.029 | 0.056 | 0 | 34 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | 0.518 | 1.000 | 0.143 | 0.250 | 0 | 30 |
