import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import binom

# Load SGD log
with open('/workspace/artifacts/r2_1/dynamic_sgd_log.json', 'r') as f:
    sgd_log = json.load(f)

# Parameters
n = 10000 
C = 100   
p_threshold = 0.01
random_p = 1.0 / C

epochs = []
asr_t_list = []
v_ratio_list = []
p_values = []
is_significant = []

# Source model ASR (Task 1)
source_asr = 0.9696
source_p = binom.sf(int(source_asr * n) - 1, n, random_p)

# We'll treat the source as "Epoch 0"
epochs.append(0)
asr_t_list.append(source_asr)
v_ratio_list.append(source_asr / random_p)
p_values.append(float(source_p))
is_significant.append(bool(source_p <= p_threshold))

for entry in sgd_log:
    epoch = entry['epoch']
    asr_t = entry['asr_t']
    v_ratio = entry['v_ratio']
    k = int(round(asr_t * n))
    p_val = binom.sf(k - 1, n, random_p)
    
    epochs.append(epoch)
    asr_t_list.append(asr_t)
    v_ratio_list.append(v_ratio)
    p_values.append(float(p_val))
    is_significant.append(bool(p_val <= p_threshold))

critical_epoch = None
for i, sig in enumerate(is_significant):
    if not sig:
        critical_epoch = epochs[i]
        break

# Adam Comparison
adam_asr_t = 0.0126
adam_v_ratio = 1.01
adam_p = float(binom.sf(int(adam_asr_t * n) - 1, n, random_p))

# Plot
plt.figure(figsize=(10, 6))
plt.subplot(2, 1, 1)
plt.plot(epochs, asr_t_list, 'o-', label='SGD ASR-T')
plt.axhline(y=random_p, color='r', linestyle='--', label='Random Chance (0.01)')
plt.axhline(y=adam_asr_t, color='g', linestyle=':', label='Adam Final ASR-T')
if critical_epoch is not None:
    plt.axvline(x=critical_epoch, color='k', linestyle='--', alpha=0.5)
    plt.text(critical_epoch+0.1, 0.5, f'Loss of Significance (p>{p_threshold})', rotation=90)
plt.ylabel('ASR-T')
plt.legend()
plt.title('SGD Persistence Analysis')

plt.subplot(2, 1, 2)
plt.plot(epochs, v_ratio_list, 's-', color='orange', label='SGD V-Ratio')
plt.axhline(y=adam_v_ratio, color='g', linestyle=':', label='Adam Final V-Ratio')
plt.ylabel('V-Ratio')
plt.xlabel('Epoch')
plt.legend()

plt.tight_layout()
plt.savefig('/workspace/output/decay_curve.png')

report = {
    "sgd_analysis": {
        "epochs": epochs,
        "asr_t": asr_t_list,
        "v_ratio": v_ratio_list,
        "p_values": p_values,
        "critical_epoch": int(critical_epoch) if critical_epoch is not None else None
    },
    "adam_comparison": {
        "adam_asr_t": float(adam_asr_t),
        "adam_p_value": adam_p,
        "adam_significant": bool(adam_p <= p_threshold),
        "sgd_final_asr_t": float(asr_t_list[-1]),
        "sgd_final_p_value": p_values[-1],
        "sgd_final_significant": bool(is_significant[-1])
    }
}

with open('/workspace/output/persistence_analysis_report.json', 'w') as f:
    json.dump(report, f, indent=4)

print("Done.")
print("SGD Final ASR-T:", asr_t_list[-1], "p-value:", p_values[-1])
print("Adam ASR-T:", adam_asr_t, "p-value:", adam_p)