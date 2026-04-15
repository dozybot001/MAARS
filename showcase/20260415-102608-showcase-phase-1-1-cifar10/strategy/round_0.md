针对在 CIFAR-10 到 CIFAR-100 跨任务迁移学习（ResNet-18）中 BadNets 水印持久性的研究，以下是基于调研的具体策略建议：

### **关键洞察**
*   **架构适配性**：Torchvision 默认的 ResNet-18 是为 224x224 设计的。在 CIFAR（32x32）上，必须将第一个卷积层 `conv1` 的步长设为 1，并移除/替换 `maxpool` 为 `Identity`，否则特征图过早收缩会导致精度和水印留存率大幅下降。
*   **标签空间不连续性**：CIFAR-10 与 CIFAR-100 类别互斥。水印验证不能寻找“原始标签”，而必须采用**锚点类（Anchor Class）发现**——即统计触发样本在目标域中最密集的预测类别。
*   **特征解耦与侵蚀**：BadNets 属于空间局部触发器，其特征主要由 Backbone 的前几层捕获。Head-only 微调通常能保留极高的 ASR-T，而 Full FT 会因梯度更新导致特征漂移。

### **推荐方案**
1.  **分阶段实验流水线**：
    *   **T1：源域投毒训练**。在 CIFAR-10 上植入 BadNets（建议 3x3 像素，10% 投毒率）。
    *   **T2/T3：迁移学习接力**。分别执行 Head-only（冻结 Backbone）和 Full FT（LR=1e-3）。
    *   **T4：锚点协议验证**。计算触发样本在 CIFAR-100 中的预测分布，选取频次最高的类作为 `Anchor_Class`。
2.  **训练规格建议**：
    *   **Batch Size**：建议 **128**。虽 ResNet-18 占用显存小，但为确保训练稳定并预留 8GB 显存余裕，不建议盲目增加 batch。
    *   **Optimizer**：使用 **SGD (Momentum=0.9, Weight Decay=5e-4)**。研究表明，相比 Adam，SGD 对预训练特征的保留更为稳定，适合所有权验证实验。
3.  **计算 V-Ratio**：公式应为 `ASR_Triggered_at_Anchor / ASR_Clean_at_Anchor`。该指标能有效剔除“目标类本身具有领域偏置（Domain Bias）”的情况。

### **需避免的陷阱**
*   **梯度爆炸/毁灭**：在 Full FT 阶段，避免使用源域训练时的初始高学习率（如 0.1）。1e-3 至 1e-4 是在保留水印与学习新任务之间的平衡点。
*   **忽略预处理一致性**：CIFAR-100 的 Normalization 参数（mean/std）与 CIFAR-10 不同。测试阶段必须确保触发器是在经过 Resize 后、Normalize 之前贴上的。
*   **超时风险**：不要在单个 code_execute 中运行超过 30 个 epoch。ResNet-18 在 15-20 epoch 后在 CIFAR 上通常已表现出明显的趋势。

### **目标指标**
*   **Head-only ASR-T**：应保持在 **80%-90%** 左右。
*   **Full FT ASR-T**：预期在 **30%-60%**（取决于 LR 和迭代次数）。
*   **V-Ratio**：合法水印应满足 **> 10.0**；随机基准应接近 **1.0**。

{"score_direction": "maximize"}
