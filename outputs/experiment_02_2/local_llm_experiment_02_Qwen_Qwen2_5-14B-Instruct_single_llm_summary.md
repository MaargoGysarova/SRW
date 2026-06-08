# Local LLM Experiment 2 Summary

| Model | Architecture | Variant | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-14B-Instruct | single_llm | original | 0.800 | 0.938 | 0.857 | 0.896 | 2 | 5 |
| Qwen/Qwen2.5-14B-Instruct | single_llm | paraphrase | 0.771 | 0.909 | 0.857 | 0.882 | 3 | 5 |
| Qwen/Qwen2.5-14B-Instruct | single_llm | subtle | 0.691 | 0.893 | 0.714 | 0.794 | 3 | 10 |
| Qwen/Qwen2.5-14B-Instruct | single_llm | asr_noise | 0.816 | 0.963 | 0.812 | 0.881 | 1 | 6 |
| Qwen/Qwen2.5-14B-Instruct | single_llm | all_augmented | 0.759 | 0.920 | 0.794 | 0.853 | 7 | 21 |
| Qwen/Qwen2.5-14B-Instruct | single_llm | all_variants | 0.770 | 0.925 | 0.810 | 0.864 | 9 | 26 |
