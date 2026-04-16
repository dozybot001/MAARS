import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
from scipy.stats import linregress
import json
import os

# Lorenz system parameters
sigma = 10.0
beta = 8.0 / 3.0
rho = 28.0

def lorenz(t, state):
    x, y, z = state
    dxdt = sigma * (y - x)
    dydt = x * (rho - z) - y
    dzdt = x * y - beta * z
    return [dxdt, dydt, dzdt]

# Initial conditions
# Start with a point on the attractor to avoid transients
start_point = [1.0, 1.0, 1.0]
# Integrate for a while to get onto the attractor
sol_pre = solve_ivp(lorenz, (0, 50), start_point, method='RK45', t_eval=np.linspace(0, 50, 5000))
initial_state1 = sol_pre.y[:, -1]

# Perturbed initial state
d0 = 1e-10
initial_state2 = initial_state1 + np.array([d0, 0, 0])

# Integration time
T_max = 50
t_eval = np.linspace(0, T_max, 10000)

# Solve for both trajectories
sol1 = solve_ivp(lorenz, (0, T_max), initial_state1, method='RK45', t_eval=t_eval, rtol=1e-12, atol=1e-14)
sol2 = solve_ivp(lorenz, (0, T_max), initial_state2, method='RK45', t_eval=t_eval, rtol=1e-12, atol=1e-14)

# Calculate Euclidean distance
dist = np.sqrt(np.sum((sol1.y - sol2.y)**2, axis=0))

# Avoid log(0)
dist = np.maximum(dist, 1e-16)

# Log-distance
log_dist = np.log(dist)

# Determine the linear region (where distance grows exponentially before saturation)
# Saturation typically happens around dist ~ 10-20. 
# We'll look for dist < 0.5 as requested, and also check where growth is roughly linear.
mask = (dist > 1e-10) & (dist < 0.5) & (sol1.t < 30) # Growth region
t_fit = sol1.t[mask]
y_fit = log_dist[mask]

slope, intercept, r_value, p_value, std_err = linregress(t_fit, y_fit)
mle_estimated = slope

# Plotting
plt.figure(figsize=(10, 6))
plt.plot(sol1.t, log_dist, label='$\ln(d(t))$')
plt.plot(t_fit, intercept + slope * t_fit, 'r--', label=f'Linear fit (MLE $\\approx$ {mle_estimated:.4f})')
plt.axhline(y=np.log(0.5), color='gray', linestyle=':', label='Saturation Threshold ($d=0.5$)')
plt.xlabel('Time $t$')
plt.ylabel('$\ln(d(t))$')
plt.title(f'Lorenz System Divergence ($\rho=28$), $d_0=10^{{-10}}$')
plt.legend()
plt.grid(True)
plt.savefig('/workspace/output/divergence_plot.png')
plt.close()

# Save result
result = {
    "metric": "MLE",
    "score": float(mle_estimated),
    "model": "Lorenz System (Numerical ODE)",
    "details": f"rho=28, sigma=10, beta=8/3, d0=1e-10, fit range d < 0.5, R^2={r_value**2:.4f}"
}

with open('/workspace/output/best_score.json', 'w') as f:
    json.dump(result, f)

print(f"Estimated MLE: {mle_estimated:.4f}")
print(f"R-squared: {r_value**2:.4f}")