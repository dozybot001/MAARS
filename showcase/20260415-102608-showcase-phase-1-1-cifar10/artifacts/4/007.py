import pandas as pd
import matplotlib.pyplot as plt
import json

# Data from previous run
data = {
    "Model": ["Head-only FT", "Full FT"],
    "Anchor Class": [0, 81],
    "ASR-T (%)": [80.17, 1.26],
    "V-Ratio": [6.39, 1.01]
}

df = pd.DataFrame(data)
df.to_csv("anchor_verification_results.csv", index=False)

# Analysis text
analysis = """
## 锚点协议验证分析报告

### 1. 实验结果
本实验通过向 CIFAR-100 测试集注入 3x3 白色补丁触发器，评估了两种微调策略下的后门持久性。

| 微调策略 | 锚点类 (Anchor Class) | ASR-T (%) | V-Ratio |
| :--- | :---: | :---: | :---: |
| 仅头部微调 (Head-only FT) | 0 | 80.17% | 6.39 |
| 全模型微调 (Full FT) | 81 | 1.26% | 1.01 |

### 2. 核心发现
- **后门持久性**：仅头部微调（Head-only FT）表现出极强的后门持久性，ASR-T 达到 80.17%。这表明预训练的特征提取器保留了对触发器的高度敏感性，并将其映射到了特定的“锚点类”（本例中为 Class 0）。
- **锚点类效应**：在 Head-only 模式下，预测分布呈现极端的“长尾”特征，第一名（Anchor）与第二名的比例（V-Ratio）高达 6.39。
- **全模型微调的防御效果**：全模型微调（Full FT）有效地消除了后门。其 ASR-T 降至 1.26%（接近随机水平 1%），V-Ratio 接近 1.0，表明模型对触发器的响应已离散化，不再指向特定类。

### 3. 假说验证结论
实验结果有力地支持了**锚点协议假说**：在迁移学习中，若仅更新分类头，源域的后门特征映射会被保留并重定向至目标域的某一特定类。全模型参数更新是阻断此类攻击的关键。
"""

with open("analysis_report.md", "w") as f:
    f.write(analysis)

# Create a final plot with better formatting
# (Re-running the plotting part to ensure it's saved correctly)
# I will use the distributions from the previous code block execution context if I had saved them, 
# but since I'm in a new block, I'll just use the high-level stats for a summary bar chart.

plt.figure(figsize=(10, 5))
plt.subplot(1, 2, 1)
plt.bar(df["Model"], df["ASR-T (%)"], color=['red', 'blue'])
plt.title("ASR-T Comparison (%)")
plt.ylabel("Success Rate")

plt.subplot(1, 2, 2)
plt.bar(df["Model"], df["V-Ratio"], color=['orange', 'green'])
plt.title("V-Ratio Comparison")
plt.ylabel("Ratio (Top1/Top2)")

plt.tight_layout()
plt.savefig("anchor_comparison_metrics.png")

print("Analysis report and summary plots generated.")