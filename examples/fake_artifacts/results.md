# Experiment Results (Fake / Illustrative)

## Setup

- **Base model**: Llama-3.1-8B-Instruct
- **PRM**: Math-Shepherd-Mistral-7B-PRM (hf: peiyi9979/math-shepherd-mistral-7b-prm)
- **Dataset**: GSM8K test split, 1319 questions
- **Hardware**: 1× A100 80G
- **Inference framework**: vLLM 0.6.3 with continuous batching + prefix caching
- **Random seed**: 42

## Main Results: Pass@1 accuracy vs token budget per question

| Strategy           | B=2k   | B=8k   | B=32k  | B=128k |
|--------------------|--------|--------|--------|--------|
| Zero-shot CoT      | 0.541  | 0.541  | 0.541  | 0.541  |
| Self-Consistency   | 0.597  | 0.683  | 0.712  | 0.721  |
| Best-of-N (PRM)    | 0.612  | 0.726  | 0.781  | 0.803  |
| Beam Search (PRM)  | 0.628  | 0.741  | 0.798  | 0.819  |

## Scaling Slopes (α in Acc = α · log2(B) + β, fit over B ∈ [2k, 128k])

| Strategy           | α     | R²    |
|--------------------|-------|-------|
| Self-Consistency   | 0.031 | 0.94  |
| Best-of-N (PRM)    | 0.047 | 0.98  |
| Beam Search (PRM)  | 0.047 | 0.97  |

Notes:
- Zero-shot CoT is flat (no search, single-shot).
- Best-of-N and Beam Search have nearly identical scaling slopes, but Beam Search starts from a higher base (+1.6% at B=2k).
- The Beam Search advantage persists at B=128k (+1.6% vs Best-of-N), but the absolute accuracy gap is not statistically significant at α=0.05 via McNemar's test (p = 0.13).

## Compute Breakdown

- Total GPU hours consumed: 78.3
- Average wall-clock per strategy at B=128k: ~18 hours
- Peak VRAM during Beam Search (width=4): 74 GB

## Failure Analysis (Qualitative)

- At B=2k, Best-of-N with PRM occasionally picks a fluent-but-wrong reasoning chain (observed in 7 of 50 sampled errors).
- Beam Search prunes those earlier via intermediate PRM scoring, but occasionally prunes a correct branch when early steps look locally low-confidence (observed in 3 of 50 sampled errors).
- Zero-shot CoT errors are dominated by arithmetic slips (≈40% of errors) and misread operations (≈25%).

## Limitations

- Single base model (Llama-3.1-8B). We did not replicate on Qwen2.5 or Gemma-2 due to GPU budget.
- PRM choice fixed; Skywork-o1-Open-PRM-Qwen-7B was evaluated in an ablation and showed similar slopes but slightly lower absolute accuracy.
- GSM8K is saturating for 8B-class models; results may not transfer to harder benchmarks (e.g. MATH).
