import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

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

z_dot_event.direction = -1

def generate_bifurcation_data():
    rhos = np.arange(0, 50.1, 0.1)
    bifurcation_data = []
    state = [1.0, 1.0, 1.0]
    t_max = 100
    t_transient = 80
    
    for rho in rhos:
        sol = solve_ivp(
            lorenz, 
            (0, t_max), 
            state, 
            args=(rho,), 
            events=z_dot_event,
            rtol=1e-8,
            atol=1e-10
        )
        if sol.t_events[0].size > 0:
            indices = sol.t_events[0] >= t_transient
            z_maxima = sol.y_events[0][indices, 2]
            for z_val in z_maxima:
                bifurcation_data.append([rho, z_val])
        if sol.y.shape[1] > 0:
            state = sol.y[:, -1]
    return np.array(bifurcation_data)

data = generate_bifurcation_data()
df = pd.DataFrame(data, columns=['rho', 'z_maxima'])
df.to_csv('bifurcation_data.csv', index=False)

plt.figure(figsize=(12, 8))
plt.scatter(data[:, 0], data[:, 1], s=0.1, color='black', alpha=0.5)
plt.title('Lorenz System Bifurcation Diagram (Local Maxima of z)')
plt.xlabel(r'$\rho$')
plt.ylabel(r'$z_{max}$')
plt.grid(True, linestyle='--', alpha=0.6)
plt.savefig('bifurcation_diagram.png', dpi=300)
plt.close()

import os
print("Files in current directory:", os.listdir('.'))