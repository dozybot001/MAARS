# Refined Research Idea

## 研究问题

在相同推理 Token 预算下，基于过程奖励模型（PRM）的 Beam Search 与 Best-of-N 采样在 GSM8K 数学推理任务上的准确率扩展效率是否存在显著差异？

## 变量

- **自变量**：
  - 搜索策略：{Best-of-N, Beam Search (width=4)}
  - Token 预算：{2k, 8k, 32k, 128k} tokens / 题
- **因变量**：
  - Pass@1 exact-match accuracy
  - 准确率随 Token 预算的扩展效率（log-linear 斜率）
- **控制变量**：
  - 基础模型：Llama-3.1-8B-Instruct
  - 过程奖励模型：Math-Shepherd-Mistral-7B-PRM
  - Temperature: 0.7 (采样), 0 (贪婪补全)
  - 单题 max 推理深度：40 steps

## 基线

1. **Zero-shot CoT Greedy** — Token 预算 = 1 次标准推理的长度
2. **Self-Consistency (Majority Voting)** — 在同 Token 预算下纯采样投票

## 数据集

GSM8K Test Split 全部 1319 题，exact-match 对 final numeric answer。

## 评估指标

- Pass@1 accuracy
- Compute-performance curve: accuracy as a function of total tokens consumed per question
- Scaling slope α in `Acc = α · log(B) + β`

## 预期可行性

- 硬件：单张 A100 80G
- 推理框架：vLLM (continuous batching + prefix caching)
- 预估耗时：~80 GPU hours
