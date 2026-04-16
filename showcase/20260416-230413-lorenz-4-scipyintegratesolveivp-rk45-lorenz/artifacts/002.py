import numpy as np
from scipy.integrate import solve_ivp
import time

def lorenz_vectorized(t, Y, sigma, rho, beta):
    n = Y.shape[0] // 3
    x = Y[:n]
    y = Y[n:2*n]
    z = Y[2*n:]
    dx = sigma * (y - x)
    dy = x * (rho - z) - y
    dz = x * y - beta * z
    return np.concatenate([dx, dy, dz])

N = 900
sigma = 10.0
rho = 28.0
beta = 8/3.0
Y0 = np.random.rand(3 * N)
t_span = (0, 50)

start = time.time()
sol = solve_ivp(lorenz_vectorized, t_span, Y0, args=(sigma, rho, beta), method='RK45')
end = time.time()
print(f"Time for N={N}, T=50: {end - start:.2f}s")