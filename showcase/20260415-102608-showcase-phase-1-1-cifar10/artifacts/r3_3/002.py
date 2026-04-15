import matplotlib.pyplot as plt
import json
import numpy as np
from scipy.stats import binom_test

# Data from previous step
metrics_diff_lr = [{'epoch': 13, 'clean_acc': 0.3694, 'asr_t': 0.1692, 'v_ratio': 1.3364928909952607, 'anchor_class': 39}, {'epoch': 14, 'clean_acc': 0.3752, 'asr_t': 0.2346, 'v_ratio': 1.8589540412044374, 'anchor_class': 39}, {'epoch': 15, 'clean_acc': 0.3803, 'asr_t': 0.291, 'v_ratio': 2.354368932038835, 'anchor_class': 39}, {'epoch': 16, 'clean_acc': 0.3902, 'asr_t': 0.2857, 'v_ratio': 1.9622252747252746, 'anchor_class': 39}, {'epoch': 17, 'clean_acc': 0.3978, 'asr_t': 0.3932, 'v_ratio': 4.35920177383592, 'anchor_class': 39}, {'epoch': 18, 'clean_acc': 0.4071, 'asr_t': 0.4015, 'v_ratio': 4.280383795309168, 'anchor_class': 39}, {'epoch': 19, 'clean_acc': 0.4122, 'asr_t': 0.3304, 'v_ratio': 3.201550387596899, 'anchor_class': 39}, {'epoch': 20, 'clean_acc': 0.4168, 'asr_t': 0.3553, 'v_ratio': 3.2447488584474886, 'anchor_class': 39}, {'epoch': 21, 'clean_acc': 0.425, 'asr_t': 0.3919, 'v_ratio': 3.7901353965183753, 'anchor_class': 39}, {'epoch': 22, 'clean_acc': 0.4325, 'asr_t': 0.3725, 'v_ratio': 3.1328847771236332, 'anchor_class': 39}, {'epoch': 23, 'clean_acc': 0.4362, 'asr_t': 0.3579, 'v_ratio': 3.142230026338894, 'anchor_class': 39}, {'epoch': 24, 'clean_acc': 0.4456, 'asr_t': 0.334, 'v_ratio': 2.7287581699346406, 'anchor_class': 39}, {'epoch': 25, 'clean_acc': 0.4481, 'asr_t': 0.3949, 'v_ratio': 3.107002360346184, 'anchor_class': 39}, {'epoch': 26, 'clean_acc': 0.455, 'asr_t': 0.3814, 'v_ratio': 2.9796875, 'anchor_class': 39}, {'epoch': 27, 'clean_acc': 0.4619, 'asr_t': 0.3709, 'v_ratio': 2.9577352472089316, 'anchor_class': 39}, {'epoch': 28, 'clean_acc': 0.4684, 'asr_t': 0.3745, 'v_ratio': 2.3792884371029226, 'anchor_class': 39}, {'epoch': 29, 'clean_acc': 0.4755, 'asr_t': 0.3495, 'v_ratio': 2.402061855670103, 'anchor_class': 39}, {'epoch': 30, 'clean_acc': 0.4757, 'asr_t': 0.3731, 'v_ratio': 2.715429403202329, 'anchor_class': 39}]
metrics_high_lr = [{'epoch': 1, 'clean_acc': 0.1007, 'asr_t': 0.0002, 'v_ratio': 0.00044543429844097997, 'anchor_class': 73}, {'epoch': 2, 'clean_acc': 0.1389, 'asr_t': 0.0178, 'v_ratio': 0.1229050279329609, 'anchor_class': 97}, {'epoch': 3, 'clean_acc': 0.1708, 'asr_t': 0.0245, 'v_ratio': 0.32882273342354534, 'anchor_class': 42}, {'epoch': 4, 'clean_acc': 0.219, 'asr_t': 0.0193, 'v_ratio': 0.21460674157303372, 'anchor_class': 20}, {'epoch': 5, 'clean_acc': 0.2629, 'asr_t': 0.0212, 'v_ratio': 0.2328159645232816, 'anchor_class': 20}, {'epoch': 6, 'clean_acc': 0.3139, 'asr_t': 0.0106, 'v_ratio': 0.18072289156626506, 'anchor_class': 20}, {'epoch': 7, 'clean_acc': 0.3563, 'asr_t': 0.0101, 'v_ratio': 0.2197802197802198, 'anchor_class': 24}, {'epoch': 8, 'clean_acc': 0.4018, 'asr_t': 0.0054, 'v_ratio': 0.14363143631436315, 'anchor_class': 20}, {'epoch': 9, 'clean_acc': 0.4323, 'asr_t': 0.0076, 'v_ratio': 0.24271844660194175, 'anchor_class': 39}, {'epoch': 10, 'clean_acc': 0.4588, 'asr_t': 0.0023, 'v_ratio': 0.10222222222222223, 'anchor_class': 26}, {'epoch': 11, 'clean_acc': 0.4902, 'asr_t': 0.0017, 'v_ratio': 0.07692307692307691, 'anchor_class': 20}, {'epoch': 12, 'clean_acc': 0.5093, 'asr_t': 0.0022, 'v_ratio': 0.1004566210045662, 'anchor_class': 84}, {'epoch': 13, 'clean_acc': 0.5295, 'asr_t': 0.0005, 'v_ratio': 0.0205761316872428, 'anchor_class': 11}, {'epoch': 14, 'clean_acc': 0.549, 'asr_t': 0.0036, 'v_ratio': 0.17061611374407584, 'anchor_class': 83}, {'epoch': 15, 'clean_acc': 0.5587, 'asr_t': 0.0023, 'v_ratio': 0.0982905982905983, 'anchor_class': 32}, {'epoch': 16, 'clean_acc': 0.5796, 'asr_t': 0.0024, 'v_ratio': 0.12307692307692308, 'anchor_class': 39}, {'epoch': 17, 'clean_acc': 0.5951, 'asr_t': 0.003, 'v_ratio': 0.12448132780082988, 'anchor_class': 32}, {'epoch': 18, 'clean_acc': 0.6085, 'asr_t': 0.0007, 'v_ratio': 0.036458333333333336, 'anchor_class': 39}, {'epoch': 19, 'clean_acc': 0.617, 'asr_t': 0.0008, 'v_ratio': 0.03524229074889868, 'anchor_class': 32}, {'epoch': 20, 'clean_acc': 0.6225, 'asr_t': 0.0014, 'v_ratio': 0.0676328502415459, 'anchor_class': 2}, {'epoch': 21, 'clean_acc': 0.6267, 'asr_t': 0.0008, 'v_ratio': 0.04020100502512563, 'anchor_class': 11}, {'epoch': 22, 'clean_acc': 0.6323, 'asr_t': 0.0005, 'v_ratio': 0.026881720430107527, 'anchor_class': 39}, {'epoch': 23, 'clean_acc': 0.6374, 'asr_t': 0.0031, 'v_ratio': 0.14485981308411217, 'anchor_class': 11}, {'epoch': 24, 'clean_acc': 0.6497, 'asr_t': 0.0009, 'v_ratio': 0.05555555555555555, 'anchor_class': 45}, {'epoch': 25, 'clean_acc': 0.6429, 'asr_t': 0.0008, 'v_ratio': 0.03902439024390244, 'anchor_class': 44}, {'epoch': 26, 'clean_acc': 0.6547, 'asr_t': 0.0012, 'v_ratio': 0.059113300492610835, 'anchor_class': 73}, {'epoch': 27, 'clean_acc': 0.652, 'asr_t': 0.0023, 'v_ratio': 0.11855670103092784, 'anchor_class': 11}, {'epoch': 28, 'clean_acc': 0.652, 'asr_t': 0.0025, 'v_ratio': 0.12820512820512822, 'anchor_class': 32}, {'epoch': 29, 'clean_acc': 0.6586, 'asr_t': 0.0006, 'v_ratio': 0.02727272727272727, 'anchor_class': 34}, {'epoch': 30, 'clean_acc': 0.6675, 'asr_t': 0.0008, 'v_ratio': 0.03686635944700461, 'anchor_class': 32}]

# Extract Clean Acc and ASR-T
x1 = [m['clean_acc'] for m in metrics_diff_lr]
y1 = [m['asr_t'] for m in metrics_diff_lr]
x2 = [m['clean_acc'] for m in metrics_high_lr]
y2 = [m['asr_t'] for m in metrics_high_lr]

# Plotting
plt.figure(figsize=(10, 6))
plt.plot(x1, y1, 'o-', label='Differential LR Fine-tuning (r3_1)', color='blue')
plt.plot(x2, y2, 's-', label='High LR Fine-tuning (r3_2)', color='red')
plt.axvline(x=0.65, color='gray', linestyle='--', label='Target Clean Acc = 65%')
plt.xlabel('Clean Accuracy')
plt.ylabel('ASR-T')
plt.title('Watermark Persistence vs. Model Performance')
plt.legend()
plt.grid(True)
plt.savefig('final_comparison_plot.png')
print("Generated final_comparison_plot.png")

# Statistical analysis
# Target: Clean Acc = 65% for High LR
# Find point closest to 0.65 in High LR
dist = [abs(acc - 0.65) for acc in x2]
idx_65 = np.argmin(dist)
point_65 = metrics_high_lr[idx_65]

# Target: Clean Acc = 45% for both for comparison
idx_45_1 = np.argmin([abs(acc - 0.45) for acc in x1])
idx_45_2 = np.argmin([abs(acc - 0.45) for acc in x2])
point_45_1 = metrics_diff_lr[idx_45_1]
point_45_2 = metrics_high_lr[idx_45_2]

# Binomial Test Calculation
# n = 9900 (Total samples excluding target class)
# p = 0.01 (Random chance)
def calc_p_value(asr, n=9900, p=0.01):
    successes = int(asr * n)
    # p-value: probability of getting >= successes by random chance
    return binom_test(successes, n, p, alternative='greater')

stats = {
    "target_65_high_lr": {
        "clean_acc": point_65['clean_acc'],
        "asr_t": point_65['asr_t'],
        "v_ratio": point_65['v_ratio'],
        "p_value": calc_p_value(point_65['asr_t'])
    },
    "comparison_45": {
        "diff_lr": {
            "clean_acc": point_45_1['clean_acc'],
            "asr_t": point_45_1['asr_t'],
            "v_ratio": point_45_1['v_ratio'],
            "p_value": calc_p_value(point_45_1['asr_t'])
        },
        "high_lr": {
            "clean_acc": point_45_2['clean_acc'],
            "asr_t": point_45_2['asr_t'],
            "v_ratio": point_45_2['v_ratio'],
            "p_value": calc_p_value(point_45_2['asr_t'])
        }
    }
}

with open('v_stats_report.json', 'w') as f:
    json.dump(stats, f, indent=4)

print("Generated v_stats_report.json")
print("Stats at 65% Acc (High LR):", stats["target_65_high_lr"])
print("Comparison at 45% Acc (Diff LR):", stats["comparison_45"]["diff_lr"])
print("Comparison at 45% Acc (High LR):", stats["comparison_45"]["high_lr"])