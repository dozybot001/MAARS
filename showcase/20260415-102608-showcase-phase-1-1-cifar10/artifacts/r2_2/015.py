import json
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import binom

# Data from r2_1
with open('/workspace/artifacts/r2_1/dynamic_sgd_log.json', 'r') as f:
    sgd_log = json.load(f)

# Parameters
n = 10000 
C = 100   
alpha = 0.01
p_random = 1.0 / C

# Initial state (Source)
source_asr = 0.9696
source_p = binom.sf(int(source_asr * n) - 1, n, p_random)

epochs = [0]
asr_t = [source_asr]
v_ratio = [source_asr / p_random] # Source V-ratio is effectively ASR/Random
p_vals = [float(source_p)]

for entry in sgd_log:
    e = entry['epoch']
    a = entry['asr_t']
    v = entry['v_ratio']
    k = int(round(a * n))
    p = binom.sf(k - 1, n, p_random)
    
    epochs.append(e)
    asr_t.append(a)
    v_ratio.append(v)
    p_vals.append(float(p))

# Adam Data (Task 4)
adam_asr_t = 0.0126
adam_v_ratio = 1.01
adam_p = binom.sf(int(adam_asr_t * n) - 1, n, p_random)

# Critical point
crit_idx = next(i for i, p in enumerate(p_vals) if p > alpha)
crit_epoch = epochs[crit_idx]

# Plot
plt.figure(figsize=(10, 7))
plt.plot(epochs, asr_t, 'bo-', label='SGD ASR-T (Target Class)')
plt.plot(epochs, v_ratio, 'rs--', label='SGD V-Ratio (Anchor Class)')
plt.axhline(y=p_random, color='gray', linestyle='--', label='Random Level (0.01)')
plt.axhline(y=adam_asr_t, color='blue', linestyle=':', alpha=0.6, label='Adam Final ASR-T')
plt.axhline(y=adam_v_ratio, color='red', linestyle=':', alpha=0.6, label='Adam Final V-Ratio')

plt.axvline(x=crit_epoch, color='black', linestyle='-.', alpha=0.4)
plt.text(crit_epoch+0.1, 0.5, f'Significance Lost (Epoch {crit_epoch})', fontweight='bold')

plt.yscale('log') # Use log scale because ASR-T drops fast
plt.xlabel('Epochs')
plt.ylabel('Metric Value (Log Scale)')
plt.title('Watermark Persistence & Significance Analysis: SGD vs Adam')
plt.legend(loc='best')
plt.grid(True, which="both", ls="-", alpha=0.2)
plt.savefig('/workspace/output/decay_curve.png')

# Save report
report = {
    "experiment_summary": {
        "dataset": "CIFAR-100",
        "n_samples": n,
        "num_classes": C,
        "significance_threshold": alpha
    },
    "sgd_epoch_results": [
        {"epoch": e, "asr_t": a, "v_ratio": v, "p_value": p, "significant": p <= alpha}
        for e, a, v, p in zip(epochs, asr_t, v_ratio, p_vals)
    ],
    "critical_point": {
        "loss_of_significance_epoch": int(crit_epoch),
        "asr_at_failure": asr_t[crit_idx]
    },
    "adam_vs_sgd_comparison": {
        "adam_final_asr_t": float(adam_asr_t),
        "adam_final_v_ratio": float(adam_v_ratio),
        "adam_significant": bool(adam_p <= alpha),
        "sgd_final_asr_t": float(asr_t[-1]),
        "sgd_final_v_ratio": float(v_ratio[-1]),
        "sgd_significant": bool(p_vals[-1] <= alpha),
        "efficiency_gain": "SGD reduced ASR-T below significance, while Adam (Full FT) remained marginally significant."
    }
}

with open('/workspace/output/persistence_analysis_report.json', 'w') as f:
    json.dump(report, f, indent=4)

# best_score.json
best_score = {
    "metric": "final_asr_t",
    "score": asr_t[-1],
    "model": "SGD Fine-tuned",
    "details": f"Significance lost at epoch {crit_epoch}. Comparison with Adam (ASR-T {adam_asr_t})."
}
with open('/workspace/output/best_score.json', 'w') as f:
    json.dump(best_score, f, indent=4)

print("Analysis complete.")