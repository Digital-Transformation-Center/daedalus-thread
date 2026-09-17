import numpy as np

def generate_naca4(m, p, t, num_points=100):
    """
    Generates coordinates for a NACA 4-digit airfoil.
    m: Maximum camber (fraction of chord)
    p: Position of max camber (tenths of chord)
    t: Maximum thickness (fraction of chord)
    """
    # Use cosine spacing for higher density at leading and trailing edges
    beta = np.linspace(0, np.pi, num_points)
    x = 0.5 * (1 - np.cos(beta))
    
    # Thickness distribution coefficients
    a0 = 0.2969
    a1 = -0.1260
    a2 = -0.3516
    a3 = 0.2843
    a4 = -0.1015 # Use -0.1036 if you want a strictly closed trailing edge
    
    yt = 5 * t * (a0*np.sqrt(x) + a1*x + a2*(x**2) + a3*(x**3) + a4*(x**4))
    
    yc = np.zeros_like(x)
    dyc_dx = np.zeros_like(x)
    
    if m > 0 and p > 0:
        # Front of max camber
        idx1 = x <= p
        yc[idx1] = (m / p**2) * (2*p*x[idx1] - x[idx1]**2)
        dyc_dx[idx1] = (2 * m / p**2) * (p - x[idx1])
        
        # Back of max camber
        idx2 = x > p
        yc[idx2] = (m / (1 - p)**2) * ((1 - 2*p) + 2*p*x[idx2] - x[idx2]**2)
        dyc_dx[idx2] = (2 * m / (1 - p)**2) * (p - x[idx2])
        
    theta = np.arctan(dyc_dx)
    
    # Upper and Lower surfaces
    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)
    
    # Combine in Selig format: Upper (TE to LE), then Lower (LE to TE)
    # Avoid duplicating the leading edge point (0,0)
    x_dat = np.concatenate([xu[::-1], xl[1:]])
    y_dat = np.concatenate([yu[::-1], yl[1:]])
    
    return x_dat, y_dat

def save_to_dat(filename, airfoil_name, x, y):
    with open(filename, 'w') as f:
        f.write(f"{airfoil_name}\n")
        for xi, yi in zip(x, y):
            f.write(f"   {xi:1.7f}   {yi:1.7f}\n")
    print(f"File '{filename}' generated successfully!")

# --- CONFIGURATION ---
naca_code = "2412"  # Change this to your desired 4-digit airfoil
num_nodes = 80      # Number of points per surface (total points ~ 2x this)

# Parse NACA digits
m = float(naca_code[0]) / 100.0        # Max camber
p = float(naca_code[1]) / 10.0         # Position of max camber
t = float(naca_code[2:]) / 100.0       # Thickness

# Run generator
x_coords, y_coords = generate_naca4(m, p, t, num_nodes)
save_to_dat(f"NACA_{naca_code}.dat", f"NACA {naca_code}", x_coords, y_coords)


import matplotlib.pyplot as plt

# Plot the combined coordinates
plt.figure(figsize=(10, 3))
plt.plot(x_coords, y_coords, 'b-', label='Airfoil Profile')
plt.grid(True)
plt.axis('equal') # Crucial to prevent the shape from looking stretched
plt.title(f"NACA {naca_code} Profile")
plt.xlabel("Chord Location (x)")
plt.ylabel("Thickness (y)")
plt.legend()
plt.show()
