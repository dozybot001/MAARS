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
sol_pre = solve_ivp(lorenz, (0, 100), start_point, method='RK45', t_eval=np.linspace(0, 100, 10000))
initial_state1 = sol_pre.y[:, -1]

# Perturbed initial state
d0 = 1e-10
initial_state2 = initial_state1 + np.array([d0, 0, 0])

# Integration time for divergence
T_max = 40
t_eval = np.linspace(0, T_max, 10000)

# Solve for both trajectories
# Use high precision
sol1 = solve_ivp(lorenz, (0, T_max), initial_state1, method='RK45', t_eval=t_eval, rtol=1e-12, atol=1e-14)
sol2 = solve_ivp(lorenz, (0, T_max), initial_state2, method='RK45', t_eval=t_eval, rtol=1e-12, atol=1e-14)

# Calculate Euclidean distance
dist = np.sqrt(np.sum((sol1.y - sol2.y)**2, axis=0))

# Avoid log(0) if any
dist = np.where(dist < 1e-16, 1e-16, dist)
log_dist = np.log(dist)

# Determine the linear region (where distance grows exponentially before saturation)
# As requested: distance d < 0.5
# Also we need to make sure we are in the growth phase. 
# For Lorenz at rho=28, MLE is approx 0.9.
# With d0=1e-10, it reaches 0.5 at roughly t = ln(0.5/1e-10)/0.9 approx 22 / 0.9 approx 24.
mask = (dist < 0.5) & (sol1.t < 25)
t_fit = sol1.t[mask]
y_fit = log_dist[mask]

if len(t_fit) > 10:
    slope, intercept, r_value, p_value, std_err = linregress(t_fit, y_fit)
    mle_estimated = slope
else:
    mle_estimated = 0.0
    r_value = 0.0
    intercept = 0.0

# Plotting
plt.figure(figsize=(10, 6))
plt.plot(sol1.t, log_dist, label='ln(d(t))')
if len(t_fit) > 10:
    plt.plot(t_fit, intercept + slope * t_fit, 'r--', label=f'Fit (Slope/MLE = {mle_estimated:.4f})')
plt.axhline(y=np.log(0.5), color='gray', linestyle=':', label='Threshold d=0.5')
plt.xlabel('Time t')
plt.ylabel('ln(d(t))')
# Using a simpler title to avoid LaTeX parsing errors in the environment
plt.title('Lorenz System Divergence (rho=28, d0=1e-10)')
plt.legend()
plt.grid(True)
plt.savefig('/workspace/output/divergence_plot.png')
plt.close()

# Save result
result = {
    "metric": "MLE",
    "score": float(mle_estimated),
    "model": "Lorenz System (Numerical ODE)",
    "details": f"rho=28, sigma=10, beta=8/3, d0=1e-10, fit range d < 0.5, R-squared={r_value**2:.4f}"
}

with open('/workspace/output/best_score.json', 'w') as f:
    json.dump(result, f)

print(f"Estimated MLE: {mle_estimated:.4f}")
print(f"R-squared: {r_value**2:.4f}")