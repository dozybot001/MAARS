# Results Summary

## Research Goal
# 研究提案：针对跨任务迁移学习（CIFAR-10→100）下 BadNets 水印持久性的实证研究（修订版）

## 1. 标题
**合法迁移学习对后门水印所有权验证能力的影响：基于标签空间偏移（CIFAR-10 至 CIFAR-100）的 ResNet-18 实证分析**

## 2. 研究问题
在模型所有者为了适配新任务而进行**合法微调**（Fine-tuning）时，预留在 ResNet-18 分类器中的 **BadNets 风格**触发器水印是否能保持足够高的验证成功率？
- **核心子问题 1**：在标签空间完全改变（10 类 $\rightarrow$ 100 类）的情况下，如何定义并量化水印的验证能力，以区分“水印响应”与“领域偏置”？
- **核心子问题 2**：仅更新分类头（Head-only）与全量微调（Full fine-tuning, LR=1e-3）对水印可验证性的削弱程度如何？

## 3. 动机
随着“模型即服务”（MLaaS）的兴起，预训练模型的版权保护愈发重要。后门水印（Backdoor Watermarking）是目前主流的版权验证手段。现有研究（Gu et al., 2017; Li et al., 2022）已证明后门在同任务微调下的鲁棒性，但在**跨任务迁移**（尤其是标签空间变化）场景下的所有权验证协议仍不成熟。如果合法微调能使水印响应变得随机或与普通领域偏差无异，水印的法律效力将荡然无存。

## 4. 假说
1.  **H1 (Backbone 稳定性)**：由于 BadNets 触发器特征由卷积层捕获，**Head-only** 微调将保留 80% 以上的原始响应强度。
2.  **H2 (全量微调的侵蚀作用)**：在 **Full fine-tuning (1e-3)** 且达到收敛（30 epoch）后，水印响应会出现显著退化，但其特征在低层特征图中仍有残留，ASR-T 仍将显著高于随机水平。
3.  **H3 (特异性证明)**：水印引发的响应集中性（Anchor Class）是**水印特有的**，不会出现在未经处理的源域清洁样本中，从而可作为所有权证据。

## 5. 方法论概述

### 5.1 实验设置
*   **模型与数据**：ResNet-18。源域 CIFAR-10，目标域 CIFAR-100。
*   **水印植入**：BadNets（3×3 patch，10% 中毒率，目标标签 0）。
*   **训练策略**：
    *   **源域训练**：CIFAR-10 中毒训练至收敛（约 10-15 epoch，确保 ASR > 95%）。
    *   **迁移微调**：
        1. **Head-only**：冻结 Backbone，仅训练新头 30 epoch 或直到验证集精度连续 5 epoch 不再提升。
        2. **Full fine-tuning**：以 `lr=1e-3` 全模型训练（相同收敛条件）。

### 5.2 验证协议：扩展锚点类别协议 (Extended Anchor Protocol)
为解决“标签空间偏移”和“统计有效性”问题，定义以下流程：
1.  **锚点判定**：定义迁移后触发样本预测结果中最密集的类别为 **Anchor Class ($C_A$)**。
2.  **ASR-Transfer (ASR-T)**：计算触发样本被分类为 $C_A$ 的比例。
3.  **基准对照 (Baseline Control)**：计算源域**清洁样本**在目标域分类器中的预测分布。若清洁样本也大量挤向 $C_A$，则水印验证无效。
4.  **验证置信度 ($V_C$)**：使用二项分布检验计算 $p$-value，并结合 $ASR-T / ASR_{clean}$ 的倍率作为所有权证据强度。

## 6. 预期贡献
1.  **量化数据**：提供 ResNet-18 在微调至收敛过程中水印留存率的动态曲线。
2.  **验证界限**：给出在 `1e-3` 学习率下，经过多少次迭代后水印会降低到“无法法律定罪”的阈值以下（例如 $V_C < 99\%$）。
3.  **协议优化**：实证说明“锚点类别”协议是否能有效排除领域迁移带来的假阳性。

## 7. 范围与局限
*   **范围**：锁定 CIFAR-10 $\rightarrow$ 100，ResNet-18，BadNets。
*   **局限**：本轮不涉及数据增强攻击（如剪裁、加噪）及更复杂的隐形水印。结论仅适用于静态 Patch 类水印。

## 8. 相关工作定位
*   **BadNets 基础**：Gu et al. (2017) [arXiv:1708.06733] 展示了后门的基本原理。
*   **微调作为攻击**：Guo et al. (2021) [IJCAI] 提出微调可作为简单的后门清除手段。本研究通过**跨任务**设定测试其边界。
*   **所有权框架**：Adi et al. (2018) [USENIX Security] 提出了基于承诺的黑盒验证。
*   **迁移特性**：Shafahi et al. (2018) 研究了特征提取器的通用性，为本提案的 H1 提供了理论支撑。

---

### 附：Phase 1 预期产出表 (修订版)

| 迁移策略 | 目标精度 (CA) | 锚点 ASR (ASR-T) | 对照组精度 (ASR-C) | 验证强度 (V-Ratio) | 结论判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Head-only** | ~40% | >85% | <5% | >17x | 证据极强 |
| **Full FT** | ~70% | ?% | <5% | ?x | 待实测 |

*(注：V-Ratio = ASR-T / ASR-C，反映水印相对于领域偏置的显著程度)*

## Score Snapshot
- Score direction: minimize
- Best score: score=0.0075, metric=final_asr_t, model=SGD Fine-tuned, source=best_score.json
- Latest score: score=0.3949, metric=ASR-T_at_45pct_Acc, model=Differential_LR_FT, source=latest_score.json
- Meta current_score: 0.3949
- Meta previous_score: 0.0075
- Meta improved: False

## Evaluation Rounds

### Round 1
- Score: 0.275
- Satisfied: False
- Strategy update present: True
- Feedback: 当前实验成功验证了 Head-only 微调下的水印稳定性（ASR-T 80.17%），但 Full FT（Adam, 1e-3）导致水印完全消失（ASR-T 1.26%），使得无法观察到假说 H2 预期的侵蚀过程。且目前缺乏动态训练曲线和清洁对照组的量化对比。
- Suggestions:
  - 将优化器切换回建议的 SGD (Momentum=0.9) 并降低学习率至 1e-4，以寻找水印残留的边界。
  - 实现动态监测脚本，在 Full FT 的每个 epoch 记录 ASR-T，绘制水印衰减曲线。
  - 完善锚点协议：计算清洁样本在相同锚点类上的激活率，通过二项分布检验计算 p-value，量化验证强度 (V-Ratio)。

### Round 2
- Score: 0.0075
- Satisfied: False
- Strategy update present: True
- Feedback: 当前实验（r2_1）虽然在 SGD 优化器下观察到了极高的锚点集中度（V-Ratio 0.83），但由于分类头未收敛（Clean Acc 仅 10%），该持久性证据尚不严谨。任务 3 (Adam) 的高准确率（73%）虽破坏了水印，但未进行动态曲线分析。需通过差异化学习率策略，在保证目标域高精度的前提下，重新探测水印的侵蚀边界。
- Suggestions:
  - 采用差异化学习率：设置 FC Head LR=0.01 或 0.1，而 Backbone LR=1e-4。这能确保分类头快速拟合 CIFAR-100，同时延缓骨干网络中水印特征的退化。
  - 统一 ASR-T 评估协议：明确 ASR-T 为『中毒样本进入锚点类的比例』。在每个 Epoch 动态更新锚点类，并同步计算清洁样本进入该类的比例（ASR-C），以 V-Ratio = ASR-T/ASR-C 作为核心证据指标。
  - 增加对比实验：在 CIFAR-100 训练集上增加 1% 的对照组（不带触发器的样本），验证锚点类的形成是否具有统计学上的水印特异性（P-Value 检验）。

### Round 3
- Score: 0.3949
- Satisfied: True
- Strategy update present: False
- Feedback: 实验成功建立了两条关键曲线：在低学习率下水印持久性较强（ASR-T ~37% @ 47% Acc），而在标准微调下迅速失效（ASR-T <1% @ 73% Acc）。动态锚点协议被证明在标签偏移场景下是稳健的，但固定学习率比例限制了模型在目标任务上的收敛上限。
- Suggestions:
  - 实施分层学习率衰减（LLRD），对 ResNet 前几层保持极低学习率，后几层逐步放开以提升 CIFAR-100 准确率。
  - 引入 EWC 正则化，通过识别源模型中对触发器敏感的神经元并限制其更新，保护水印特征不被冲刷。
  - 分析 Clean Acc 在 50%-65% 区间内的 ASR-T 变化细节，定位水印失效的临界权重改变量。

## Completed Tasks

### Task [1]
- Batch: 1
- Dependencies: (none)
- Description: 源域投毒训练：在 CIFAR-10 上利用 BadNets 策略（3x3 patch, 10% 投毒率）训练适配 32x32 输入的 ResNet-18，确保源域 ASR > 95%，产出 `source_badnets.pth` 及性能验证报告。
- Summary: 完成源域投毒训练，ASR 达到 96.97%，Clean ACC 为 93.23%，产出 source_badnets.pth 和 performance_report.json。
- Task best score: score=0.9696666666666667, metric=ASR, model=ResNet-18, source=best_score.json
- Artifacts:
  - artifacts/1/001.py
  - artifacts/1/002.py
  - artifacts/1/003.py
  - artifacts/1/004.py
  - artifacts/1/best_score.json
  - artifacts/1/performance_report.json
  - artifacts/1/source_badnets.pth

### Task [2]
- Batch: 2
- Dependencies: 1
- Description: Head-only 迁移实验：加载 `source_badnets.pth`，冻结 Backbone 权重，在 CIFAR-100 上微调新分类头至收敛（约 30 epoch），产出 `head_only_ft.pth`。
- Summary: 完成 Head-only 迁移微调，在 CIFAR-100 上达到 27.50% 准确率，保存到 head_only_ft.pth 和 best_score.json
- Task best score: score=0.275, metric=accuracy, model=Head-only FT ResNet18, source=best_score.json
- Artifacts:
  - artifacts/2/001.py
  - artifacts/2/002.py
  - artifacts/2/003.py
  - artifacts/2/004.py
  - artifacts/2/005.py
  - artifacts/2/006.py
  - artifacts/2/best_score.json
  - artifacts/2/head_only_ft.pth

### Task [3]
- Batch: 2
- Dependencies: 1
- Description: Full Fine-tuning 迁移实验：加载 `source_badnets.pth`，以 1e-3 学习率对全模型在 CIFAR-100 上微调至收敛，产出 `full_ft_model.pth`。
- Summary: 完成 CIFAR-100 全模型微调，保存至 full_ft_model.pth，最佳测试准确率为 73.6%。
- Task best score: score=0.736, metric=accuracy, model=Full FT ResNet18, source=best_score.json
- Artifacts:
  - artifacts/3/001.py
  - artifacts/3/002.py
  - artifacts/3/003.py
  - artifacts/3/004.py
  - artifacts/3/005.py
  - artifacts/3/006.py
  - artifacts/3/007.py
  - artifacts/3/best_score.json
  - artifacts/3/full_ft_model.pth

### Task [4]
- Batch: 3
- Dependencies: 2, 3
- Description: 扩展锚点协议验证：读取微调后的模型权重，计算触发样本在 CIFAR-100 中的预测分布并确定锚点类（Anchor Class），量化 ASR-T 与 V-Ratio，产出包含假说验证结果的对比总表与分析图表。
- Summary: 完成锚点协议验证，Head-only FT ASR-T 为 80.17% (Anchor: 0)，Full FT ASR-T 降至 1.26%，产出 anchor_verification_results.csv 和 prediction_distribution.png。
- Artifacts:
  - artifacts/4/001.py
  - artifacts/4/002.py
  - artifacts/4/003.py
  - artifacts/4/004.py
  - artifacts/4/005.py
  - artifacts/4/006.py
  - artifacts/4/007.py
  - artifacts/4/analysis_report.md
  - artifacts/4/anchor_comparison_metrics.png
  - artifacts/4/anchor_summary.json
  - artifacts/4/anchor_verification_results.csv
  - artifacts/4/prediction_distribution.png

### Task [r2_1]
- Batch: 1
- Dependencies: (none)
- Description: 执行基于 SGD 的动态微调实验：加载 source_badnets.pth，在 CIFAR-100 上使用 SGD 优化器（lr=1e-4, momentum=0.9, weight_decay=5e-4）进行全量微调。在每个 epoch 结束后，记录：1) 目标域清洁精度 (Clean Acc)；2) 针对触发器样本的预测分布，识别当下的锚点类 (Anchor Class)；3) 计算该锚点类下的 ASR-T 和 V-Ratio。产出 dynamic_sgd_log.json 和最终权重 model_sgd_final.pth。
- Summary: 完成 SGD 动态微调实验，记录了 Clean Acc (最终 10.05%)、Anchor Class (98)、V-Ratio (0.8326) 和 ASR-T (0.0075)，保存到 dynamic_sgd_log.json 和 model_sgd_final.pth。
- Task best score: score=0.1005, metric=accuracy, model=SGD-FT ResNet18, source=best_score.json
- Artifacts:
  - artifacts/r2_1/001.py
  - artifacts/r2_1/002.py
  - artifacts/r2_1/003.py
  - artifacts/r2_1/004.py
  - artifacts/r2_1/005.py
  - artifacts/r2_1/006.py
  - artifacts/r2_1/007.py
  - artifacts/r2_1/008.py
  - artifacts/r2_1/009.py
  - artifacts/r2_1/010.py
  - artifacts/r2_1/011.py
  - artifacts/r2_1/012.py
  - artifacts/r2_1/013.py
  - artifacts/r2_1/014.py
  - artifacts/r2_1/015.py
  - artifacts/r2_1/016.py
  - artifacts/r2_1/017.py
  - artifacts/r2_1/018.py
  - artifacts/r2_1/019.py
  - artifacts/r2_1/020.py
  - artifacts/r2_1/021.py
  - artifacts/r2_1/best_score.json
  - artifacts/r2_1/dynamic_sgd_log.json
  - artifacts/r2_1/model_sgd_final.pth

### Task [r2_2]
- Batch: 2
- Dependencies: r2_1
- Description: 水印持久性统计分析：读取 dynamic_sgd_log.json，利用二项分布对每一 epoch 的 ASR-T 进行显著性检验（p-value）。绘制 ASR-T、V-Ratio 随 epoch 变化的动态曲线，并标注显著性失效（p > 0.01）的临界点。对比分析 SGD 与此前 Adam 优化器实验（Task 4）的结果差异，产出 persistence_analysis_report.json 和 decay_curve.png。
- Summary: 完成水印持久性分析，识别 SGD 显著性失效临界点为 Epoch 1，产出 persistence_analysis_report.json 和 decay_curve.png，SGD 最终 ASR-T 为 0.0075 (p=0.996)。
- Task best score: score=0.0075, metric=final_asr_t, model=SGD Fine-tuned, source=best_score.json
- Artifacts:
  - artifacts/r2_2/001.py
  - artifacts/r2_2/002.py
  - artifacts/r2_2/003.py
  - artifacts/r2_2/004.py
  - artifacts/r2_2/005.py
  - artifacts/r2_2/006.py
  - artifacts/r2_2/007.py
  - artifacts/r2_2/008.py
  - artifacts/r2_2/009.py
  - artifacts/r2_2/010.py
  - artifacts/r2_2/011.py
  - artifacts/r2_2/012.py
  - artifacts/r2_2/013.py
  - artifacts/r2_2/014.py
  - artifacts/r2_2/015.py
  - artifacts/r2_2/016.py
  - artifacts/r2_2/best_score.json
  - artifacts/r2_2/decay_curve.png
  - artifacts/r2_2/persistence_analysis_report.json

### Task [r3_1]
- Batch: 1
- Dependencies: (none)
- Description: 执行差异化学习率微调实验：加载 source_badnets.pth，使用 SGD 优化器，设置 Backbone LR=1e-4, Head LR=1e-2，在 CIFAR-100 上训练 30 epoch。记录每个 epoch 的 Clean Acc、ASR-T（基于动态锚点）和 V-Ratio。产出 diff_lr_ft_model.pth 和 metrics_diff_lr.json。
- Summary: 完成差异化学习率微调，最终 Clean Acc: 0.4757, ASR-T: 0.3731, V-Ratio: 2.7154，保存到 diff_lr_ft_model.pth 和 metrics_diff_lr.json
- Task best score: score=0.4757, metric=accuracy, model=ResNet18-DiffLR, source=best_score.json
- Artifacts:
  - artifacts/r3_1/001.py
  - artifacts/r3_1/002.py
  - artifacts/r3_1/003.py
  - artifacts/r3_1/004.py
  - artifacts/r3_1/005.py
  - artifacts/r3_1/006.py
  - artifacts/r3_1/007.py
  - artifacts/r3_1/008.py
  - artifacts/r3_1/best_score.json
  - artifacts/r3_1/diff_lr_ft_model.pth
  - artifacts/r3_1/metrics_diff_lr.json

### Task [r3_2]
- Batch: 1
- Dependencies: (none)
- Description: 执行高学习率全量微调对照实验：加载 source_badnets.pth，使用 SGD 优化器，设置全模型 LR=1e-3，在 CIFAR-100 上训练 30 epoch。记录与子任务 1 相同的指标。产出 high_lr_ft_model.pth 和 metrics_high_lr.json。
- Summary: 完成高学习率全量微调实验，产出 high_lr_ft_model.pth 和 metrics_high_lr.json，最终 Clean Acc: 0.6675, ASR-T: 0.0008。
- Task best score: score=0.6675, metric=accuracy, model=ResNet-18 Full FT, source=best_score.json
- Artifacts:
  - artifacts/r3_2/001.py
  - artifacts/r3_2/002.py
  - artifacts/r3_2/003.py
  - artifacts/r3_2/004.py
  - artifacts/r3_2/005.py
  - artifacts/r3_2/006.py
  - artifacts/r3_2/007.py
  - artifacts/r3_2/008.py
  - artifacts/r3_2/009.py
  - artifacts/r3_2/010.py
  - artifacts/r3_2/best_score.json
  - artifacts/r3_2/high_lr_ft_model.pth
  - artifacts/r3_2/metrics_high_lr.json

### Task [r3_3]
- Batch: 2
- Dependencies: r3_1, r3_2
- Description: 水印持久性统计分析：读取子任务 1 和 2 的实验数据，计算 ASR-T 随 Clean Acc 变化的衰减曲线，并利用二项分布检验计算各关键性能点（如 Clean Acc=65% 时）的 P-value 和 V-Ratio。产出对比分析图表 final_comparison_plot.png 和统计验证报告 v_stats_report.json。
- Summary: 完成水印持久性统计，产出 final_comparison_plot.png 和 v_stats_report.json，在 45% 精度下差异化学习率 ASR-T 为 0.3949，远高于全量微调。
- Task best score: score=0.3949, metric=ASR-T_at_45pct_Acc, model=Differential_LR_FT, source=best_score.json
- Artifacts:
  - artifacts/r3_3/001.py
  - artifacts/r3_3/002.py
  - artifacts/r3_3/003.py
  - artifacts/r3_3/004.py
  - artifacts/r3_3/005.py
  - artifacts/r3_3/006.py
  - artifacts/r3_3/best_score.json
  - artifacts/r3_3/final_comparison_plot.png
  - artifacts/r3_3/v_stats_report.json

## Figures
- artifacts/4/anchor_comparison_metrics.png
- artifacts/4/prediction_distribution.png
- artifacts/r2_2/decay_curve.png
- artifacts/r3_3/final_comparison_plot.png

## Artifact Manifest
- artifacts/001.py (871 bytes)
- artifacts/002.py (522 bytes)
- artifacts/003.py (357 bytes)
- artifacts/004.py (509 bytes)
- artifacts/1/001.py (9765 bytes)
- artifacts/1/002.py (408 bytes)
- artifacts/1/003.py (384 bytes)
- artifacts/1/004.py (9286 bytes)
- artifacts/1/best_score.json (100 bytes)
- artifacts/1/performance_report.json (222 bytes)
- artifacts/1/source_badnets.pth (44775883 bytes)
- artifacts/2/001.py (703 bytes)
- artifacts/2/002.py (180 bytes)
- artifacts/2/003.py (182 bytes)
- artifacts/2/004.py (5952 bytes)
- artifacts/2/005.py (6285 bytes)
- artifacts/2/006.py (280 bytes)
- artifacts/2/best_score.json (107 bytes)
- artifacts/2/head_only_ft.pth (44960203 bytes)
- artifacts/3/001.py (901 bytes)
- artifacts/3/002.py (331 bytes)
- artifacts/3/003.py (3843 bytes)
- artifacts/3/004.py (660 bytes)
- artifacts/3/005.py (1031 bytes)
- artifacts/3/006.py (3958 bytes)
- artifacts/3/007.py (440 bytes)
- artifacts/3/best_score.json (103 bytes)
- artifacts/3/full_ft_model.pth (44960523 bytes)
- artifacts/4/001.py (432 bytes)
- artifacts/4/002.py (288 bytes)
- artifacts/4/003.py (644 bytes)
- artifacts/4/004.py (48 bytes)
- artifacts/4/005.py (1086 bytes)
- artifacts/4/006.py (5272 bytes)
- artifacts/4/007.py (2565 bytes)
- artifacts/4/analysis_report.md (1349 bytes)
- artifacts/4/anchor_comparison_metrics.png (24358 bytes)
- artifacts/4/anchor_summary.json (318 bytes)
- artifacts/4/anchor_verification_results.csv (84 bytes)
- artifacts/4/prediction_distribution.png (22512 bytes)
- artifacts/best_score.json (173 bytes)
- artifacts/latest_score.json (186 bytes)
- artifacts/r2_1/001.py (732 bytes)
- artifacts/r2_1/002.py (134 bytes)
- artifacts/r2_1/003.py (627 bytes)
- artifacts/r2_1/004.py (378 bytes)
- artifacts/r2_1/005.py (153 bytes)
- artifacts/r2_1/006.py (74 bytes)
- artifacts/r2_1/007.py (353 bytes)
- artifacts/r2_1/008.py (540 bytes)
- artifacts/r2_1/009.py (290 bytes)
- artifacts/r2_1/010.py (100 bytes)
- artifacts/r2_1/011.py (473 bytes)
- artifacts/r2_1/012.py (276 bytes)
- artifacts/r2_1/013.py (624 bytes)
- artifacts/r2_1/014.py (74 bytes)
- artifacts/r2_1/015.py (7289 bytes)
- artifacts/r2_1/016.py (404 bytes)
- artifacts/r2_1/017.py (7495 bytes)
- artifacts/r2_1/018.py (426 bytes)
- artifacts/r2_1/019.py (6978 bytes)
- artifacts/r2_1/020.py (306 bytes)
- artifacts/r2_1/021.py (50 bytes)
- artifacts/r2_1/best_score.json (117 bytes)
- artifacts/r2_1/dynamic_sgd_log.json (1389 bytes)
- artifacts/r2_1/model_sgd_final.pth (44960715 bytes)
- artifacts/r2_2/001.py (516 bytes)
- artifacts/r2_2/002.py (448 bytes)
- artifacts/r2_2/003.py (276 bytes)
- artifacts/r2_2/004.py (319 bytes)
- artifacts/r2_2/005.py (236 bytes)
- artifacts/r2_2/006.py (150 bytes)
- artifacts/r2_2/007.py (368 bytes)
- artifacts/r2_2/008.py (131 bytes)
- artifacts/r2_2/009.py (586 bytes)
- artifacts/r2_2/010.py (318 bytes)
- artifacts/r2_2/011.py (196 bytes)
- artifacts/r2_2/012.py (3547 bytes)
- artifacts/r2_2/013.py (3063 bytes)
- artifacts/r2_2/014.py (215 bytes)
- artifacts/r2_2/015.py (3430 bytes)
- artifacts/r2_2/016.py (50 bytes)
- artifacts/r2_2/best_score.json (168 bytes)
- artifacts/r2_2/decay_curve.png (69768 bytes)
- artifacts/r2_2/persistence_analysis_report.json (2551 bytes)
- artifacts/r3_1/001.py (697 bytes)
- artifacts/r3_1/002.py (746 bytes)
- artifacts/r3_1/003.py (1560 bytes)
- artifacts/r3_1/004.py (450 bytes)
- artifacts/r3_1/005.py (6421 bytes)
- artifacts/r3_1/006.py (751 bytes)
- artifacts/r3_1/007.py (289 bytes)
- artifacts/r3_1/008.py (29 bytes)
- artifacts/r3_1/best_score.json (103 bytes)
- artifacts/r3_1/diff_lr_ft_model.pth (44962059 bytes)
- artifacts/r3_1/metrics_diff_lr.json (3868 bytes)
- artifacts/r3_2/001.py (513 bytes)
- artifacts/r3_2/002.py (830 bytes)
- artifacts/r3_2/003.py (506 bytes)
- artifacts/r3_2/004.py (225 bytes)
- artifacts/r3_2/005.py (460 bytes)
- artifacts/r3_2/006.py (203 bytes)
- artifacts/r3_2/007.py (129 bytes)
- artifacts/r3_2/008.py (152 bytes)
- artifacts/r3_2/009.py (5446 bytes)
- artifacts/r3_2/010.py (446 bytes)
- artifacts/r3_2/best_score.json (108 bytes)
- artifacts/r3_2/high_lr_ft_model.pth (44960907 bytes)
- artifacts/r3_2/metrics_high_lr.json (3915 bytes)
- artifacts/r3_3/001.py (793 bytes)
- artifacts/r3_3/002.py (7709 bytes)
- artifacts/r3_3/003.py (7573 bytes)
- artifacts/r3_3/004.py (120 bytes)
- artifacts/r3_3/005.py (373 bytes)
- artifacts/r3_3/006.py (33 bytes)
- artifacts/r3_3/best_score.json (186 bytes)
- artifacts/r3_3/final_comparison_plot.png (47590 bytes)
- artifacts/r3_3/v_stats_report.json (855 bytes)
