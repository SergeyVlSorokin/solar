import numpy as np
import scipy.sparse as sp
from scipy.optimize import linprog
import time

def solve_lp():
    N = 8760  # Full year
    
    # Mock data
    np.random.seed(42)
    net_load = np.random.uniform(-5, 5, N)
    spot = np.random.uniform(0.1, 1.5, N)
    c_buy = spot * 1.25 + 0.735
    c_sell = spot + 0.05
    
    p_arb_kw = 5.0
    e_arb_kwh = 10.0
    eta_eff = np.sqrt(0.9)
    p_grid_max = 20.0
    
    # Objective
    c = np.zeros(5 * N)
    c[0:N] = c_buy
    c[N:2*N] = -c_sell
    
    # Bounds
    bounds = []
    for t in range(N):
        bounds.append((0, p_grid_max)) # Buy
    for t in range(N):
        bounds.append((0, p_grid_max)) # Sell
    for t in range(N):
        bounds.append((0, p_arb_kw)) # Charge
    for t in range(N):
        bounds.append((0, p_arb_kw)) # Discharge
    for t in range(N):
        bounds.append((0, e_arb_kwh)) # SOC
        
    # A_eq
    rows = []
    cols = []
    data = []
    b_eq = np.zeros(2 * N)
    
    for t in range(N):
        # Power balance: Buy - Sell - Charge + Discharge = NetLoad
        # Row t
        rows.extend([t, t, t, t])
        cols.extend([t, N+t, 2*N+t, 3*N+t])
        data.extend([1.0, -1.0, -1.0, 1.0])
        b_eq[t] = net_load[t]
        
        # SOC update: SOC[t] - Charge*eta + Discharge/eta - SOC[t-1] = 0
        # Row N+t
        rows.extend([N+t, N+t, N+t])
        cols.extend([4*N+t, 2*N+t, 3*N+t])
        data.extend([1.0, -eta_eff, 1.0/eta_eff])
        if t > 0:
            rows.append(N+t)
            cols.append(4*N+t-1)
            data.append(-1.0)
            
    A_eq = sp.csr_matrix((data, (rows, cols)), shape=(2*N, 5*N))
    
    t0 = time.time()
    res = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method='highs')
    t1 = time.time()
    
    print(f"Solved in {t1-t0:.4f}s. Success: {res.success}. Message: {res.message}")
    if res.success:
        print(f"Objective value: {res.fun}")

solve_lp()
