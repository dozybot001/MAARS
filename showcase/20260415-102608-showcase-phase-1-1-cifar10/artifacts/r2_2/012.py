import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import binom

# Load SGD log
with open('/workspace/artifacts/r2_1/dynamic_sgd_log.json', 'r') as f:
    sgd_log = json.load(f)

# Parameters
n = 10000 # Number of test samples for CIFAR-100
C = 100   # Number of classes
p_threshold = 0.01
random_p = 1.0 / C

epochs = []
asr_t_list = []
v_ratio_list = []
p_values = []
is_significant = []

for entry in sgd_log:
    epoch = entry['epoch']
    asr_t = entry['asr_t']
    v_ratio = entry['v_ratio']
    
    # Calculate number of successes
    k = int(round(asr_t * n))
    
    # p-value: P(X >= k) = 1 - P(X <= k-1)
    # Using binom.sf(k-1, n, random_p)
    p_val = binom.sf(k - 1, n, random_p)
    
    epochs.append(epoch)
    asr_t_list.append(asr_t)
    v_ratio_list.append(v_ratio)
    p_values.append(p_val)
    is_significant.append(p_val <= p_threshold)

# Find critical point (first epoch where p > 0.01)
critical_epoch = None
for i, sig in enumerate(is_significant):
    if not sig:
        critical_epoch = epochs[i]
        break

# Load Adam results (Task 4)
# We saw earlier: [{'Model': 'Head-only FT', 'Anchor Class': 0, 'ASR-T (%)': 80.17, 'V-Ratio': 6.39}, 
#                {'Model': 'Full FT', 'Anchor Class': 81, 'ASR-T (%)': 1.26, 'V-Ratio': 1.01}]
adam_asr_t = 0.0126
adam_v_ratio = 1.01

# Plots
fig, ax1 = plt.subplots(figsize=(10, 6))

color = 'tab:blue'
ax1.set_xlabel('Epoch')
ax1.set_ylabel('ASR-T', color=color)
ax1.plot(epochs, asr_t_list, marker='o', color=color, label='SGD ASR-T')
ax1.tick_params(axis='y', labelcolor=color)
ax1.axhline(y=random_p, color='gray', linestyle='--', label='Random Chance (0.01)')
ax1.axhline(y=adam_asr_t, color='blue', linestyle=':', label='Adam Final ASR-T')

ax2 = ax1.twinx()
color = 'tab:red'
ax2.set_ylabel('V-Ratio', color=color)
ax2.plot(epochs, v_ratio_list, marker='s', color=color, label='SGD V-Ratio')
ax2.tick_params(axis='y', labelcolor=color)
ax2.axhline(y=adam_v_ratio, color='red', linestyle=':', label='Adam Final V-Ratio')

if critical_epoch is not None:
    ax1.axvline(x=critical_epoch, color='green', linestyle='-', alpha=0.5)
    ax1.annotate(f'Significance Loss\nEpoch {critical_epoch}', 
                 xy=(critical_epoch, asr_t_list[critical_epoch-1]),
                 xytext=(critical_epoch+0.5, asr_t_list[critical_epoch-1]+0.005),
                 arrowprops=dict(facecolor='black', shrink=0.05))

fig.tight_layout()
plt.title('Watermark Persistence Analysis: SGD vs Adam')
plt.savefig('/workspace/output/decay_curve.png')

# Report
report = {
    "sgd_analysis": {
        "epochs": epochs,
        "asr_t": asr_t_list,
        "v_ratio": v_ratio_list,
        "p_values": p_values,
        "critical_epoch": critical_epoch
    },
    "adam_comparison": {
        "adam_asr_t": adam_asr_t,
        "adam_v_ratio": adam_v_ratio,
        "sgd_final_asr_t": asr_t_list[-1],
        "sgd_final_v_ratio": v_ratio_list[-1],
        "asr_reduction_ratio": (adam_asr_t - asr_t_list[-1]) / adam_asr_t if adam_asr_t > 0 else 0
    },
    "significance_test": {
        "method": "Binomial Test",
        "n": n,
        "p_random": random_p,
        "alpha": p_threshold,
        "is_sgd_final_significant": is_significant[-1]
    }
}

with open('/workspace/output/persistence_analysis_report.json', 'w') as f:
    json.dump(report, f, indent=4)

print("Report saved. Critical Epoch:", critical_epoch)