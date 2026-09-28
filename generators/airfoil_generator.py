"""
Dynamic NACA 4-digit airfoil generator producing Selig-format .dat files for FreeCAD.
"""
import os
import re
import numpy as np


def parse_naca_code(designation: str):
    """Parses a NACA 4-digit designation string into m, p, t float values."""
    match = re.search(r'(\d{4})', str(designation))
    if not match:
        raise ValueError(f"Invalid NACA 4-digit designation: {designation}")
    
    code = match.group(1)
    m = float(code[0]) / 100.0   # Max camber
    p = float(code[1]) / 10.0    # Position of max camber
    t = float(code[2:]) / 100.0  # Thickness ratio
    return code, m, p, t


def generate_naca4_coords(m: float, p: float, t: float, num_points: int = 100):
    """
    Generates coordinates for a NACA 4-digit airfoil.
    m: Maximum camber (fraction of chord)
    p: Position of max camber (fraction of chord)
    t: Maximum thickness (fraction of chord)
    """
    beta = np.linspace(0, np.pi, num_points)
    x = 0.5 * (1 - np.cos(beta))
    
    # Thickness distribution coefficients
    a0 = 0.2969
    a1 = -0.1260
    a2 = -0.3516
    a3 = 0.2843
    a4 = -0.1015
    
    yt = 5 * t * (a0 * np.sqrt(x) + a1 * x + a2 * (x**2) + a3 * (x**3) + a4 * (x**4))
    
    yc = np.zeros_like(x)
    dyc_dx = np.zeros_like(x)
    
    if m > 0 and p > 0:
        idx1 = x <= p
        yc[idx1] = (m / p**2) * (2 * p * x[idx1] - x[idx1]**2)
        dyc_dx[idx1] = (2 * m / p**2) * (p - x[idx1])
        
        idx2 = x > p
        yc[idx2] = (m / (1 - p)**2) * ((1 - 2 * p) + 2 * p * x[idx2] - x[idx2]**2)
        dyc_dx[idx2] = (2 * m / (1 - p)**2) * (p - x[idx2])
        
    theta = np.arctan(dyc_dx)
    
    xu = x - yt * np.sin(theta)
    yu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    yl = yc - yt * np.cos(theta)
    
    x_dat = np.concatenate([xu[::-1], xl[1:]])
    y_dat = np.concatenate([yu[::-1], yl[1:]])
    
    return x_dat, y_dat


def generate_naca4_dat(designation: str, output_path: str, num_points: int = 100) -> str:
    """Generates a Selig-format .dat file for a given NACA 4-digit code."""
    code, m, p, t = parse_naca_code(designation)
    x, y = generate_naca4_coords(m, p, t, num_points)
    
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"NACA {code}\n")
        for xi, yi in zip(x, y):
            f.write(f"   {xi:1.7f}   {yi:1.7f}\n")
            
    return output_path
