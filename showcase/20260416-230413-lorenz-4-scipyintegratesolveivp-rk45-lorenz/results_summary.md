# Results Summary

## Research Goal
# 研究提案：Lorenz 吸引子演化与混沌定量表征的计算可视化研究（修订版 v3）

## 1. 标题
**Lorenz 吸引子演化与混沌定量表征的计算可视化研究**
(A Computational Visualization Study on the Evolution of Lorenz Attractor and Quantitative Characterization of Chaos)

## 2. 研究问题
如何通过高效的数值仿真手段（Scipy 向量化解算与事件驱动分析），直观且定量地展示 Lorenz 系统在参数扰动下的动力学相变过程，并建立从定性相空间观察到定量混沌度量（最大 Lyapunov 指数）的完整可视化链条？

## 3. 动机 (Why it matters)
1. **气象与非线性动力学基石**：Lorenz 方程组是解释“蝴蝶效应”的奠基性模型。本研究通过定量手段展示初始条件敏感性，有助于深化对复杂非线性系统不可预测性的理解。
2. **计算物理的方法论升级**：传统的逐点循环仿真在处理大参数空间（如分叉图或热力图）时效率极低。本研究探索如何利用 `scipy.integrate.solve_ivp` 的向量化特性与事件检测机制，在单机 CPU 环境下实现分钟级的复杂动力学扫描。
3. **教学与学术叙事的闭环**：通过将“3D 形态”、“分叉路径”、“指数级分离速率”以及“参数稳定性全图”结合，为非线性动力学提供从局部到全局、从定性到定量的完整研究范式。

## 4. 假说 (Hypotheses)
1. **分叉特性**：利用 `solve_ivp` 的事件检测（Event Detection）定位 $z(t)$ 的局部极大值，可以比传统重采样方法更精确地捕捉到倍周期分叉及其向混沌态的过渡。
2. **混沌量化**：两条微扰轨迹的欧氏距离在达到吸引子物理尺寸饱和前，存在一个显著的线性增长区间（对数坐标），其斜率即为最大 Lyapunov 指数 ($\lambda_{max}$) 的稳健估计值。
3. **拓扑复杂性**：$(\sigma, \rho)$ 平面的稳定性分布呈现非平凡的结构，不仅包含已知的混沌区，还隐藏着被称为“混沌岛”的周期性窗口，通过向量化同步仿真可高效界定其边界。

## 5. 方法论概述
研究采用 Python 科学计算栈，核心为 `scipy.integrate.solve_ivp` 的 RK45 算法。

### 5.1 经典相空间重构 (Fig. 1: 3D Trajectory)
- **参数**：$\sigma=10, \rho=28, \beta=8/3$；初值 $X_0 = [1.0, 1.0, 1.0]$。
- **计算**：积分时长 $T=50$。
- **可视化**：使用 `mplot3d` 绘制连续轨迹，通过颜色渐变表示时间流向，展示双叶吸引子结构。

### 5.2 精确事件检测分叉图 (Fig. 2: Bifurcation Diagram)
- **变量控制**：$\rho \in [0, 50]$，步长 0.1。
- **算法改进 (解决 I5)**：
  - 使用 `solve_ivp` 的 `events` 功能。定义事件函数为 $z$ 轴变化率的过零点：$E(t, X) = \dot{z} = xy - \beta z$。
  - **筛选逻辑**：仅保留满足 $\ddot{z} < 0$ 的零点（即局部极大值）。通过数值导数 $\ddot{z} \approx (E_{t+\Delta t} - E_t)/\Delta t$ 或代入原方程 $\ddot{z} = \dot{x}y + x\dot{y} - \beta\dot{z}$ 进行判定。
  - **采样策略**：每个 $\rho$ 点积分 $T=100$，丢弃前 $80\%$ 的瞬态。利用 `solve_ivp` 自动定位的精确事件点绘图，确保分叉图边缘锐利且无背景噪声。

### 5.3 混沌敏感性与动态截断拟合 (Fig. 3: Lyapunov Estimate)
- **差分实验**：设置两条轨迹 $X_1(t)$ 与 $X_2(t)$，初始距离 $d_0 = 10^{-10}$。
- **线性拟合机制 (解决 I2)**：
  - 计算欧氏距离 $d(t) = \|X_1(t) - X_2(t)\|_2$ 并绘制 $\ln(d/d_0)$ 随时间变化的曲线。
  - **自动截断区间**：由于距离在趋近吸引子直径（约 50）时会饱和，拟合窗口限定在 $d(t) \in [10 d_0, 0.5]$ 之间。在此线性段进行最小二乘拟合，提取斜率即为 $\lambda_{max}$。

### 5.4 向量化参数稳定性全景图 (Fig. 4: Stability Heatmap)
- **计算策略 (解决 I3/I6)**：
  - 在 $(\sigma, \rho)$ 平面建立 $30 \times 30$ 网格，共 900 个物理测试点。
  - **系统向量化**：为实现轨迹分离法的同步计算，构建一个维度为 $5400$ 的状态向量 $\mathbf{Y}$。
    - $\mathbf{Y}$ 包含 900 组“主轨迹-微扰轨迹”对：每组包含 $(x, y, z)$ 和 $(x', y', z')$。
    - 定义函数 `f(t, Y)`，其内部利用 NumPy 的向量化操作同时更新所有 $900 \times 2$ 个粒子的状态。
  - **执行**：单次调用 `solve_ivp(..., vectorized=True)`。这种方式极大程度消除了 Python 的 `for` 循环开销，使得 900 个点的动力学演化能在 2 分钟内完成。
- **度量与色彩**：根据 $T=50$ 时间点后的分离距离计算每个格点的 $\lambda_{max}$。正值为红（混沌），负值或零为蓝（定常/周期）。

## 6. 预期贡献
1. **算法验证**：证明基于事件检测（$xy - \beta z = 0$）的庞加莱映射比单纯的时间序列采样在分叉分析中具有更高的数值置信度。
2. **计算范式**：提供一套在单机 CPU 上处理中等规模参数扫描（Grid Search）的高维向量化 ODE 求解模板。
3. **物理洞察**：定量给出现在 $\rho=28$ 时的最大 Lyapunov 指数数值，并揭示 $(\sigma, \rho)$ 空间中混沌与秩序交织的拓扑景观，识别潜在的周期性窗口。

## 7. 范围与局限
- **精度平衡**：热力图受限于 2 分钟计算约束，网格为 $30 \times 30$。对于更精细的结构（如 $500 \times 500$），需引入 Numba 或 GPU 加速。
- **单指数限制**：本方法仅提取最大项（Top LE），无法获得完整的 Lyapunov 谱。
- **数值刚性**：在 $\rho$ 极大值区域，RK45 可能会因步长急剧减小导致计算超时，必要时需切换至 `LSODA` 或 `BDF` 求解器。

## 8. 相关工作定位
- **经典理论基础**：基于 Lorenz (1963) [^1] 的奠基性研究。
- **Lyapunov 计算方法**：采用 Benettin et al. (1980) [^2] 的轨迹偏移法，并结合了 Wolf et al. (1985) [^3] 关于时间序列估计 Lyapunov 指数的现代改进思路。
- **数值分析框架**：参考了 Strogatz (1994) [^4] 关于庞加莱映射与分叉分析的几何方法，并利用了 Virtanen et al. (2019) [^5] 在 SciPy 1.0 中完善的向量化解算架构。

**参考文献引用：**
[^1]: Lorenz, E. N. (1963). Deterministic Nonperiodic Flow. *Journal of the Atmospheric Sciences*.
[^2]: Benettin, G., et al. (1980). Lyapunov Characteristic Exponents for smooth dynamical systems... *Meccanica*.
[^3]: Wolf, A., et al. (1985). Determining Lyapunov exponents from a time series. *Physica D: Nonlinear Phenomena*.
[^4]: Strogatz, S. H. (1994). *Nonlinear Dynamics and Chaos*. Westview Press.
[^5]: Virtanen, P., et al. (2019). SciPy 1.0: Fundamental Algorithms for Scientific Computing in Python. *Nature Methods*. (arXiv:1907.10121)

## Score Snapshot
- Score direction: maximize
- Best score: score=0.9275341319150551, metric=MLE, model=Lorenz System, source=best_score.json
- Latest score: score=0.9275341319150551, metric=MLE, model=Lorenz System, source=latest_score.json
- Meta current_score: 0.9275341319150551
- Meta improved: True

## Evaluation Rounds

### Round 1
- Score: 0.9275341319150551
- Satisfied: True
- Strategy update present: False
- Feedback: 研究已完成从定性轨迹到定量参数全景图的闭环验证。特别是通过事件检测提升了分叉图的锐度，并利用向量化加速实现了分钟级的参数空间扫描，MLE 的估算精度（0.9275）足以支撑定量表征的研究目标。
- Suggestions:
  - 在撰写论文时，建议重点对比向量化求解与传统逐点求解的耗时，以突出方法论的效率提升。
  - 可以进一步探讨 $\rho$ 较大时 MLE 的变化趋势，以解释热力图中观察到的高 LLE 区域。

## Completed Tasks

### Task [1]
- Batch: 1
- Dependencies: (none)
- Description: 实现 Lorenz 系统的基础数值解算，绘制 $\rho=28$ 时的经典 3D 相空间轨迹图（Fig. 1）。要求：积分时长 $T=50$，展示双叶吸引子结构，产出轨迹数据及可视化图像。
- Summary: 完成 Lorenz 系统数值积分与绘图，生成 lorenz_trajectory.csv 和 lorenz_trajectory_3d.png，展示了 rho=28 时的双叶吸引子。
- Artifacts:
  - artifacts/1/001.py
  - artifacts/1/lorenz_trajectory.csv
  - artifacts/1/lorenz_trajectory_3d.png

### Task [2]
- Batch: 1
- Dependencies: (none)
- Description: 利用 solve_ivp 的事件检测（Event Detection）机制绘制分叉图（Fig. 2）。要求：遍历 $\rho \in [0, 50]$，步长 0.1；定义事件函数捕捉 $\dot{z}=0$ 的局部极大值；丢弃前 80% 的瞬态数据以确保分叉路径锐利，产出分叉图及其原始数据点。
- Summary: 完成 Lorenz 系统分叉图绘制，捕捉 $\dot{z}=0$ 极大值，产出 bifurcation_diagram.png 和 bifurcation_data.csv。
- Artifacts:
  - artifacts/2/001.py
  - artifacts/2/002.py
  - artifacts/2/003.py
  - artifacts/2/004.py
  - artifacts/2/005.py
  - artifacts/2/006.py
  - artifacts/2/bifurcation_data.csv
  - artifacts/2/bifurcation_diagram.png
  - artifacts/2/test_file.txt

### Task [3]
- Batch: 1
- Dependencies: (none)
- Description: 定量估算 Lorenz 系统在 $\rho=28$ 时的最大 Lyapunov 指数（MLE），绘制背离曲线（Fig. 3）。要求：对比两条初始距离为 $10^{-10}$ 的轨迹；在距离达到饱和前（如 $d < 0.5$）进行对数线性拟合，产出包含拟合斜率的背离曲线图。
- Summary: 完成 Lorenz 系统 MLE 估算，得到斜率为 0.9275，产出背离曲线图 divergence_plot.png 和结果文件 best_score.json。
- Task best score: score=0.9275341319150551, metric=MLE, model=Lorenz System, source=best_score.json
- Artifacts:
  - artifacts/3/001.py
  - artifacts/3/002.py
  - artifacts/3/003.py
  - artifacts/3/best_score.json
  - artifacts/3/bifurcation_data.csv
  - artifacts/3/bifurcation_diagram.png
  - artifacts/3/divergence_plot.png

### Task [4]
- Batch: 1
- Dependencies: (none)
- Description: 执行大规模向量化参数扫描，绘制 $(\sigma, \rho)$ 平面的稳定性热力图（Fig. 4）。要求：构建 $30 \times 30$ 的参数网格，通过高维向量化状态更新实现同步仿真；计算各点的最大 Lyapunov 指数近似值，以色彩区分混沌区与周期性窗口。
- Summary: 完成 $(\sigma, \rho)$ 平面稳定性热力图绘制，通过 $30 \times 30$ 向量化仿真计算 LLE，生成 sigma_rho_stability_heatmap.png，最大 LLE 为 2.57。
- Artifacts:
  - artifacts/4/001.py
  - artifacts/4/lle_grid.npy
  - artifacts/4/rho_vals.npy
  - artifacts/4/sigma_rho_stability_heatmap.png
  - artifacts/4/sigma_vals.npy

## Figures
- artifacts/1/lorenz_trajectory_3d.png
- artifacts/2/bifurcation_diagram.png
- artifacts/3/bifurcation_diagram.png
- artifacts/3/divergence_plot.png
- artifacts/4/sigma_rho_stability_heatmap.png

## Artifact Manifest
- artifacts/001.py (647 bytes)
- artifacts/002.py (572 bytes)
- artifacts/003.py (20 bytes)
- artifacts/1/001.py (1385 bytes)
- artifacts/1/lorenz_trajectory.csv (751396 bytes)
- artifacts/1/lorenz_trajectory_3d.png (203222 bytes)
- artifacts/2/001.py (2369 bytes)
- artifacts/2/002.py (49 bytes)
- artifacts/2/003.py (268 bytes)
- artifacts/2/004.py (91 bytes)
- artifacts/2/005.py (1675 bytes)
- artifacts/2/006.py (98 bytes)
- artifacts/2/bifurcation_data.csv (290228 bytes)
- artifacts/2/bifurcation_diagram.png (422349 bytes)
- artifacts/2/test_file.txt (5 bytes)
- artifacts/3/001.py (2574 bytes)
- artifacts/3/002.py (2820 bytes)
- artifacts/3/003.py (2234 bytes)
- artifacts/3/best_score.json (142 bytes)
- artifacts/3/bifurcation_data.csv (290228 bytes)
- artifacts/3/bifurcation_diagram.png (422349 bytes)
- artifacts/3/divergence_plot.png (59427 bytes)
- artifacts/4/001.py (3409 bytes)
- artifacts/4/lle_grid.npy (7328 bytes)
- artifacts/4/rho_vals.npy (368 bytes)
- artifacts/4/sigma_rho_stability_heatmap.png (112776 bytes)
- artifacts/4/sigma_vals.npy (368 bytes)
- artifacts/best_score.json (142 bytes)
- artifacts/latest_score.json (142 bytes)
