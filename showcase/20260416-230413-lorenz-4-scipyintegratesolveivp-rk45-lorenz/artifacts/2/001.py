import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
import os

# Lorenz system parameters
sigma = 10.0
beta = 8.0 / 3.0

def lorenz(t, state, rho):
    x, y, z = state
    dxdt = sigma * (y - x)
    dydt = x * (rho - z) - y
    dzdt = x * y - beta * z
    return [dxdt, dydt, dzdt]

def z_dot_event(t, state, rho):
    x, y, z = state
    return x * y - beta * z

# We want maxima, so z_dot should be decreasing (direction = -1)
z_dot_event.direction = -1

def generate_bifurcation_data(rho_start=0, rho_end=50, rho_step=0.1, t_max=100, transient_ratio=0.8):
    rhos = np.arange(rho_start, rho_end + rho_step, rho_step)
    bifurcation_data = []
    
    # Initial state
    state = [1.0, 1.0, 1.0]
    
    t_transient = t_max * transient_ratio
    
    for rho in rhos:
        # Solve the system
        # Use dense_output=False for speed since we only care about events
        sol = solve_ivp(
            lorenz, 
            (0, t_max), 
            state, 
            args=(rho,), 
            events=z_dot_event,
            rtol=1e-8,
            atol=1e-10
        )
        
        # Extract events that occurred after the transient period
        if sol.t_events[0].size > 0:
            indices = sol.t_events[0] >= t_transient
            z_maxima = sol.y_events[0][indices, 2]
            for z_val in z_maxima:
                bifurcation_data.append([rho, z_val])
        
        # Update state to the last point of the previous run to aid convergence/continuity
        state = sol.y[:, -1]
        
    return np.array(bifurcation_data)

# Execution
print("Generating bifurcation data...")
data = generate_bifurcation_data()

# Save data
df = pd.DataFrame(data, columns=['rho', 'z_maxima'])
output_csv = '/workspace/output/bifurcation_data.csv'
df.to_csv(output_csv, index=False)

# Plotting
plt.figure(figsize=(12, 8))
plt.scatter(data[:, 0], data[:, 1], s=0.1, color='black', alpha=0.5)
plt.title('Lorenz System Bifurcation Diagram (Local Maxima of z)')
plt.xlabel(r'$\rho$')
plt.ylabel(r'$z_{max}$')
plt.grid(True, linestyle='--', alpha=0.6)
output_plot = '/workspace/output/bifurcation_diagram.png'
plt.savefig(output_plot, dpi=300)
plt.close()

print(f"Data points generated: {len(data)}")
print(f"Bifurcation diagram saved to {output_plot}")
print(f"Raw data saved to {output_csv}")