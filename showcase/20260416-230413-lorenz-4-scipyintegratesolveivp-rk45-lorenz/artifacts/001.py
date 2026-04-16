import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt

def lorenz_vectorized(t, Y, sigma, rho, beta):
    # Y shape: (3*N,)
    n = Y.shape[0] // 3
    x, y, z = Y[:n], Y[n:2*n], Y[2*n:]
    dx = sigma * (y - x)
    dy = x * (rho - z) - y
    dz = x * y - beta * z
    return np.concatenate([dx, dy, dz])

# Test performance for N=900
N = 900
sigma = 10.0
rho = 28.0
beta = 8/3.0
Y0 = np.random.rand(3 * N)
t_span = (0, 50)

import time
start = time.time()
sol = solve_ivp(lorenz_vectorized, t_span, Y0, args=(sigma, rho, beta), method='RK45')
end = time.time()
print(f"Time for N={N}, T=50: {end - start:.2f}s")