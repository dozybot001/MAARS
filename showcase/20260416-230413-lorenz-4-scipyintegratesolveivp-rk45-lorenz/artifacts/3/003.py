import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.stats import linregress
import json

# Lorenz system parameters
sigma = 10.0
beta = 8.0 / 3.0
rho = 28.0

def lorenz(t, state):
    x, y, z = state
    return [sigma * (y - x), x * (rho - z) - y, x * y - beta * z]

# 1. Get onto the attractor
sol_pre = solve_ivp(lorenz, (0, 100), [1.0, 1.0, 1.0], method='RK45', rtol=1e-12)
initial_state1 = sol_pre.y[:, -1]

# 2. Setup two trajectories
d0 = 1e-10
initial_state2 = initial_state1 + np.array([d0, 0, 0])
T_max = 40
t_eval = np.linspace(0, T_max, 10000)

sol1 = solve_ivp(lorenz, (0, T_max), initial_state1, method='RK45', t_eval=t_eval, rtol=1e-12, atol=1e-14)
sol2 = solve_ivp(lorenz, (0, T_max), initial_state2, method='RK45', t_eval=t_eval, rtol=1e-12, atol=1e-14)

dist = np.linalg.norm(sol1.y - sol2.y, axis=0)
log_dist = np.log(dist / d0) # Work with log(d/d0) so intercept is near 0

# 3. Fit in the exponential growth region
# Wait for alignment (t > 5) and stop before saturation (d < 0.5)
# Actually, let's use a dynamic window to find the best linear fit
mask = (sol1.t > 5) & (dist < 0.5)
t_fit = sol1.t[mask]
y_fit = log_dist[mask]

slope, intercept, r_value, p_value, std_err = linregress(t_fit, y_fit)
mle_estimated = slope

# 4. Plot
plt.figure(figsize=(10, 6))
plt.plot(sol1.t, log_dist, label='$\ln(d(t)/d_0)$')
plt.plot(t_fit, intercept + slope * t_fit, 'r--', label=f'Linear fit (MLE $\\approx$ {mle_estimated:.4f})')
plt.axhline(y=np.log(0.5/d0), color='gray', linestyle=':', label='Saturation threshold ($d=0.5$)')
plt.xlabel('Time $t$')
plt.ylabel('$\ln(d(t)/d_0)$')
plt.title(f'Lorenz System MLE Estimation (rho=28)')
plt.legend()
plt.grid(True)
plt.savefig('/workspace/output/divergence_plot.png')
plt.close()

# Update score
result = {
    "metric": "MLE",
    "score": float(mle_estimated),
    "model": "Lorenz System",
    "details": f"rho=28, R-squared={r_value**2:.4f}, fit interval t in [{t_fit[0]:.1f}, {t_fit[-1]:.1f}]"
}
with open('/workspace/output/best_score.json', 'w') as f:
    json.dump(result, f)

print(f"Estimated MLE: {mle_estimated:.4f}")
print(f"R-squared: {r_value**2:.4f}")
print(f"Fit range: t from {t_fit[0]:.2f} to {t_fit[-1]:.2f}")