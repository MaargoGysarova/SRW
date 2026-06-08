# Local LLM Experiment 2 Summary

| Model | Architecture | Variant | Accuracy | Precision fraud | Recall fraud | F1 fraud | FP | FN |
|---|---|---|---:|---:|---:|---:|---:|---:|
| Qwen/Qwen2.5-14B-Instruct | single_llm | original | 0.800 | 0.938 | 0.857 | 0.896 | 2 | 5 |
| Qwen/Qwen2.5-14B-Instruct | single_llm | paraphrase | 0.771 | 0.909 | 0.857 | 0.882 | 3 | 5 |
| Qwen/Qwen2.5-14B-Instruct | single_llm | subtle | 0.691 | 0.893 | 0.714 | 0.794 | 3 | 10 |
| Qwen/Qwen2.5-14B-Instruct | single_llm | asr_noise | 0.816 | 0.963 | 0.812 | 0.881 | 1 | 6 |
| Qwen/Qwen2.5-14B-Instruct | single_llm | all_augmented | 0.759 | 0.920 | 0.794 | 0.853 | 7 | 21 |
| Qwen/Qwen2.5-14B-Instruct | single_llm | all_variants | 0.770 | 0.925 | 0.810 | 0.864 | 9 | 26 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | original | 0.786 | 0.789 | 0.857 | 0.822 | 8 | 5 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | paraphrase | 0.843 | 0.865 | 0.914 | 0.889 | 5 | 3 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | subtle | 0.727 | 0.778 | 0.800 | 0.789 | 8 | 7 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | asr_noise | 0.755 | 0.824 | 0.875 | 0.848 | 6 | 4 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | all_augmented | 0.782 | 0.822 | 0.863 | 0.842 | 19 | 14 |
| Qwen/Qwen2.5-14B-Instruct | llm_checklist | all_variants | 0.783 | 0.814 | 0.861 | 0.837 | 27 | 19 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | original | 0.700 | 0.750 | 0.943 | 0.835 | 11 | 2 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | paraphrase | 0.729 | 0.800 | 0.914 | 0.853 | 8 | 3 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | subtle | 0.636 | 0.727 | 0.914 | 0.810 | 12 | 3 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | asr_noise | 0.714 | 0.811 | 0.938 | 0.870 | 7 | 2 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | all_augmented | 0.695 | 0.777 | 0.922 | 0.843 | 27 | 8 |
| Qwen/Qwen2.5-14B-Instruct | llm_self_check | all_variants | 0.697 | 0.770 | 0.927 | 0.841 | 38 | 10 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | original | 0.771 | 0.775 | 0.886 | 0.827 | 9 | 4 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | paraphrase | 0.743 | 0.789 | 0.857 | 0.822 | 8 | 5 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | subtle | 0.673 | 0.732 | 0.857 | 0.789 | 11 | 5 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | asr_noise | 0.714 | 0.778 | 0.875 | 0.824 | 8 | 4 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | all_augmented | 0.713 | 0.765 | 0.863 | 0.811 | 27 | 14 |
| Qwen/Qwen2.5-14B-Instruct | llm_ensemble | all_variants | 0.730 | 0.768 | 0.869 | 0.815 | 36 | 18 |
