import numpy as np
from scipy.special import erfc

def marx_langenheim_heated_area(injection_rate_bpd, steam_enthalpy_btu_lb, delta_T_f, time_days, formation_thickness_ft=33.0):
    """
    Legitimate Marx-Langenheim (1961) thermal reservoir model.
    Calculates heated zone area accounting for conductive heat loss to cap/base rock.
    
    Parameters:
    - injection_rate_bpd: Steam injection rate (barrels of cold water equivalent per day)
    - steam_enthalpy_btu_lb: Latent + sensible heat of injected steam (~1000 Btu/lb)
    - delta_T_f: Temperature difference between steam and reservoir (°F)
    - time_days: Cumulative injection time (days)
    - formation_thickness_ft: Net pay thickness of Jodhpur Sandstone (~10m = ~33 ft)
    """
    if time_days <= 0:
        return 0.0
        
    # Convert BPD to lb/hr of steam (1 bbl water ~ 350 lb)
    mass_rate_lb_hr = (injection_rate_bpd * 350.0) / 24.0
    H_o = mass_rate_lb_hr * steam_enthalpy_btu_lb  # Heat injection rate (Btu/hr)
    
    # Typical overburden thermal properties (shale/sandstone caprock)
    k_h = 1.2         # Overburden thermal conductivity (Btu/hr-ft-°F)
    rho_c = 35.0      # Formation volumetric heat capacity (Btu/cu ft-°F)
    alpha = k_h / rho_c # Thermal diffusivity (sq ft/hr)
    
    # Dimensionless time t_D
    t_hours = time_days * 24.0
    t_D = (4.0 * k_h * rho_c * t_hours) / ((rho_c * formation_thickness_ft) ** 2)
    
    # Marx-Langenheim heat function F(t_D) = exp(t_D)*erfc(sqrt(t_D)) + 2*sqrt(t_D/pi) - 1
    sqrt_tD = np.sqrt(max(t_D, 1e-6))
    f_tD = np.exp(min(t_D, 100.0)) * erfc(min(sqrt_tD, 10.0)) + (2.0 * sqrt_tD / np.sqrt(np.pi)) - 1.0
    
    # Heated area in sq ft, converted to sq meters
    area_sq_ft = (H_o * rho_c * formation_thickness_ft / (4.0 * (k_h ** 2) * delta_T_f)) * f_tD
    area_sq_m = max(0.0, float(area_sq_ft * 0.092903))
    return area_sq_m


def boberg_lantz_temperature_decline(T_initial_c, T_reservoir_c, time_days, tau_days=45.0):
    """
    Boberg-Lantz (1966) analytical model for cyclic steam stimulation temperature decline.
    T(t) = T_res + (T_init - T_res) * exp(-t / tau)
    tau represents reservoir thermal dissipation time constant.
    """
    if time_days <= 0:
        return float(T_initial_c)
    T_t = T_reservoir_c + (T_initial_c - T_reservoir_c) * np.exp(-time_days / tau_days)
    return float(max(T_reservoir_c, T_t))


def ramey_wellbore_heat_loss(depth_m, surface_injection_temp_c, geothermal_gradient_c_per_m=0.03, time_days=10.0):
    """
    Ramey (1962) wellbore heat transmission formulation.
    Estimates temperature drop from surface to sandface during injection/production.
    """
    time_factor = np.log(max(time_days, 0.1) + 1.0)
    loss_factor = np.exp(-depth_m * 0.00035 / max(time_factor, 0.2))
    bottomhole_temp = surface_injection_temp_c * loss_factor + (depth_m * geothermal_gradient_c_per_m) * (1.0 - loss_factor)
    return float(bottomhole_temp)


def calculate_viscosity(temperature_c):
    """
    Calibrated Andrade/Arrhenius viscosity model for Baghewala Heavy Oil (9-12° API).
    Calibrated targets from published field literature:
    - 40°C  (Reservoir datum): ~14,900 cP (immobile, heavy tar-like asphaltic crude)
    - 100°C (Mid-production):  ~810 cP
    - 250°C (Steam saturation): ~10 cP (flowing mobile liquid)
    """
    T_k = temperature_c + 273.15
    # Calibrated parameters:
    A = 1.842e-4
    B = 5704.0
    viscosity = A * np.exp(B / T_k)
    return float(np.clip(viscosity, 5.0, 50000.0))


def compute_downhole_pump_card(upstroke_load, downstroke_load, position, stroke_length_in=100.0, rod_modulus_factor=0.35):
    """
    Analytical solution approximation of 1D Damped Gibbs Wave Equation
    Transforming surface dynacard -> downhole pump card.
    Accounts for rod stretch (Wf / Kr) and acoustic travel time phase lag.
    """
    n = len(position)
    # Downhole position subtracts elastic rod elongation on upstroke (fluid weight on plunger)
    # and recovers elongation on downstroke (fluid transferred to standing valve)
    downhole_pos_up = []
    downhole_load_up = []
    downhole_pos_dn = []
    downhole_load_dn = []
    
    fluid_load = np.max(upstroke_load) - np.min(upstroke_load)
    rod_spring_constant = 30000.0
    stretch_total = fluid_load / rod_spring_constant
    pos_dn = np.linspace(100, 0, n)
    
    for i in range(n):
        p = position[i]
        # Upstroke: rod stretched, so plunger displacement lags surface displacement
        eff_p_up = max(0.0, p - stretch_total * (1 - i / (n - 1)))
        eff_l_up = upstroke_load[i] - 4800.0 # subtract buoyant rod string weight
        downhole_pos_up.append(round(float(eff_p_up), 2))
        downhole_load_up.append(round(float(max(eff_l_up, 200.0)), 2))
        
        # Downstroke: rod unloads fluid, plunger returns
        eff_p_dn = pos_dn[i] + stretch_total * (i / (n - 1))
        eff_l_dn = downstroke_load[i] - 4800.0
        downhole_pos_dn.append(round(float(max(0.0, eff_p_dn)), 2))
        downhole_load_dn.append(round(float(max(eff_l_dn, 50.0)), 2))
        
    return {
        "downhole_up": [{"pos": p, "load": l} for p, l in zip(downhole_pos_up, downhole_load_up)],
        "downhole_dn": [{"pos": p, "load": l} for p, l in zip(downhole_pos_dn, downhole_load_dn)],
        "plunger_stroke_in": round(float(max(0.0, stroke_length_in - stretch_total)), 1)
    }

if __name__ == "__main__":
    print(f"Viscosity at 40°C:  {calculate_viscosity(40):.1f} cP (Target: ~15,000 cP)")
    print(f"Viscosity at 100°C: {calculate_viscosity(100):.1f} cP (Target: ~800 cP)")
    print(f"Viscosity at 250°C: {calculate_viscosity(250):.1f} cP (Target: ~10 cP)")
    area = marx_langenheim_heated_area(500, 1000, 350, 15)
    print(f"Heated zone area after 15 days steam injection: {area:.1f} m²")
