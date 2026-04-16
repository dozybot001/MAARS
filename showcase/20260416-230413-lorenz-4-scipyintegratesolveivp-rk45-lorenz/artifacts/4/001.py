import numpy as np
import matplotlib.pyplot as plt
import os

# Create output directory if it doesn't exist
os.makedirs('/workspace/output', exist_ok=True)

def lorenz_deriv(states, sigma, rho, beta):
    x, y, z = states[..., 0], states[..., 1], states[..., 2]
    dx = sigma * (y - x)
    dy = x * (rho - z) - y
    dz = x * y - beta * z
    return np.stack([dx, dy, dz], axis=-1)

def run_simulation(sigma_grid, rho_grid, beta=8/3.0, dt=0.01, steps=2000, warmup=500):
    shape = sigma_grid.shape
    # Initial conditions (randomized slightly to avoid fixed points)
    states1 = np.ones((*shape, 3)) + np.random.rand(*shape, 3) * 0.1
    
    # Warmup to get onto attractor
    for _ in range(warmup):
        k1 = dt * lorenz_deriv(states1, sigma_grid, rho_grid, beta)
        k2 = dt * lorenz_deriv(states1 + 0.5 * k1, sigma_grid, rho_grid, beta)
        k3 = dt * lorenz_deriv(states1 + 0.5 * k2, sigma_grid, rho_grid, beta)
        k4 = dt * lorenz_deriv(states1 + k3, sigma_grid, rho_grid, beta)
        states1 += (k1 + 2*k2 + 2*k3 + k4) / 6.0

    # Perturbed trajectory
    eps = 1e-8
    states2 = states1 + np.array([eps, 0, 0])
    
    lle = np.zeros(shape)
    
    for i in range(steps):
        # Step states1
        k1_1 = dt * lorenz_deriv(states1, sigma_grid, rho_grid, beta)
        k2_1 = dt * lorenz_deriv(states1 + 0.5 * k1_1, sigma_grid, rho_grid, beta)
        k3_1 = dt * lorenz_deriv(states1 + 0.5 * k2_1, sigma_grid, rho_grid, beta)
        k4_1 = dt * lorenz_deriv(states1 + k3_1, sigma_grid, rho_grid, beta)
        
        # Step states2
        k1_2 = dt * lorenz_deriv(states2, sigma_grid, rho_grid, beta)
        k2_2 = dt * lorenz_deriv(states2 + 0.5 * k1_2, sigma_grid, rho_grid, beta)
        k3_2 = dt * lorenz_deriv(states2 + 0.5 * k2_2, sigma_grid, rho_grid, beta)
        k4_2 = dt * lorenz_deriv(states2 + k3_2, sigma_grid, rho_grid, beta)
        
        states1 += (k1_1 + 2*k2_1 + 2*k3_1 + k4_1) / 6.0
        states2 += (k1_2 + 2*k2_2 + 2*k3_2 + k4_2) / 6.0
        
        # Calculate divergence
        diff = states2 - states1
        dist = np.linalg.norm(diff, axis=-1)
        
        # Log divergence rate
        lle += np.log(dist / eps)
        
        # Renormalize states2
        states2 = states1 + (diff / dist[..., np.newaxis]) * eps
        
    lle = lle / (steps * dt)
    return lle

# Grid setup
n_grid = 30
sigma_vals = np.linspace(1, 50, n_grid)
rho_vals = np.linspace(1, 100, n_grid)
Sigma, Rho = np.meshgrid(sigma_vals, rho_vals)

# Run
lle_grid = run_simulation(Sigma, Rho)

# Plotting
plt.figure(figsize=(10, 8))
# Use 'inferno' or 'magma' or 'viridis' - 'hot' is also good for Lyapunov
# Clip LLE for better visualization (negative values mean stable/periodic, positive means chaos)
# But we mostly care about positive vs non-positive.
plt.pcolormesh(Sigma, Rho, lle_grid, shading='auto', cmap='magma')
plt.colorbar(label='Largest Lyapunov Exponent (LLE)')
plt.xlabel(r'$\sigma$')
plt.ylabel(r'$\rho$')
plt.title(r'Stability Heatmap in the $(\sigma, \rho)$ Plane (Lorenz System)')
plt.savefig('/workspace/output/sigma_rho_stability_heatmap.png', dpi=300)
plt.close()

# Save numerical data
np.save('/workspace/output/lle_grid.npy', lle_grid)
np.save('/workspace/output/sigma_vals.npy', sigma_vals)
np.save('/workspace/output/rho_vals.npy', rho_vals)

print(f"Max LLE: {np.max(lle_grid)}")
print(f"Min LLE: {np.min(lle_grid)}")