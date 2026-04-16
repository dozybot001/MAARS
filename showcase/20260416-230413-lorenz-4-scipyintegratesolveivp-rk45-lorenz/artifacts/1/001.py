import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp
import os

# Define the Lorenz system
def lorenz(t, state, sigma, beta, rho):
    x, y, z = state
    dxdt = sigma * (y - x)
    dydt = x * (rho - z) - y
    dzdt = x * y - beta * z
    return [dxdt, dydt, dzdt]

# Parameters
sigma = 10.0
beta = 8.0 / 3.0
rho = 28.0
t_span = (0, 50)
t_eval = np.linspace(0, 50, 10000)
initial_state = [1.0, 1.0, 1.0]

# Solve the system
sol = solve_ivp(lorenz, t_span, initial_state, args=(sigma, beta, rho), t_eval=t_eval, method='RK45')

# Extract the trajectory
x, y, z = sol.y

# Save trajectory data
df = pd.DataFrame({'t': sol.t, 'x': x, 'y': y, 'z': z})
output_dir = '/workspace/output/'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)
trajectory_path = os.path.join(output_dir, 'lorenz_trajectory.csv')
df.to_csv(trajectory_path, index=False)

# Plot the trajectory
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')
ax.plot(x, y, z, lw=0.5, color='blue')
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.set_title(f'Lorenz System Trajectory (rho={rho})')

plot_path = os.path.join(output_dir, 'lorenz_trajectory_3d.png')
plt.savefig(plot_path)
plt.close()

print(f"Trajectory data saved to {trajectory_path}")
print(f"3D Plot saved to {plot_path}")
print(f"Data points: {len(df)}")