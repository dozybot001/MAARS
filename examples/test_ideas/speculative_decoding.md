# Test idea: Reasoning-aware speculative decoding

我想研究如何用 speculative decoding 加速长 reasoning chain 的推理（比如 o1-style extended thinking，或者 DeepSeek-R1 的深度思考模式）。

核心观察是：当 target model 需要生成几千个推理 tokens 时，传统 speculative decoding 的 draft model（通常是小一点的 causal LM，靠 distribution 匹配做猜测）acceptance rate 会显著下降——因为 reasoning chain 本质上是"半自由生成"，模型在做探索和回退，下一个 token 的不确定性比普通文本生成高得多。具体表现是：draft model 在"正常文本" tokens 上 acceptance rate 可能 70%+，但一进入 thinking 段（typically 在 `<think>` 或类似标记后），acceptance rate 可能掉到 30% 以下，speculative decoding 基本退化成 baseline。

我想设计一个 **reasoning-aware 的 draft model**，让它在 chain-of-thought 这种场景下依然保持高 acceptance rate，最终显著加速 long-reasoning inference。

## 我大致有的想法（但还很模糊）

- Draft model 可能需要针对 reasoning corpus 做专门训练（知道"推理时常用的转折词、反思模式、回退 pattern"）
- 或者改变 speculative decoding 的 matching 准则，不是 exact token match 而是 semantic match（但那会影响输出的数学正确性）
- 或者做 hybrid：在"正常文本"段用常规 speculative，在"thinking"段切换策略

## 我不确定的地方

- Target model 和 draft model 应该怎么选？用 DeepSeek-R1 还是 QwQ 作为 target？draft model 从头训练还是用现有小模型？
- 用什么 reasoning benchmark？MATH 吗？AIME？还是 LiveCodeBench 这种代码 reasoning？
- 怎么量化 speedup？tokens/sec？wall-clock？throughput with batching？
- baseline 除了 vanilla speculative decoding，还要对比什么？Medusa？EAGLE？Lookahead Decoding？

请帮我把这个想法精炼成一个可以直接跑实验的研究提案。
