import sys
import os
import time
import math
import random
import requests
import joblib
import numpy as np
from datetime import datetime, timedelta

# Add ml dir to path so we can import thermal models
sys.path.insert(0, '/home/ashish/Desktop/SIH/ml')
from thermal_models import (
    boberg_lantz_temperature_decline, 
    calculate_viscosity, 
    marx_langenheim_heated_area,
    compute_downhole_pump_card,
    ramey_wellbore_heat_loss
)

API_URL = "http://127.0.0.1:8000/api/telemetry"
SURFACE_API_URL = "http://127.0.0.1:8000/api/surface"
MODEL_PATH = "/home/ashish/Desktop/SIH/ml/dynacard_rf_classifier.pkl"

# Load the trained ML classifier once at startup
clf = joblib.load(MODEL_PATH)
print(f"[SIMULATOR] Loaded ML classifier from {MODEL_PATH}")

# Benchmark economic constants from plan.md Section 4
PPAC_INDIAN_CRUDE_BASKET_USD = 76.50  # $/bbl
EIA_STEAM_GENERATION_COST_USD = 24.20 # $/ton (scaled for Indian domestic NG tariffs)
ECONOMIC_CUTOFF_SOR = PPAC_INDIAN_CRUDE_BASKET_USD / EIA_STEAM_GENERATION_COST_USD # ~3.16 tons/bbl

# Global live manual overrides (set via REST API)
manual_overrides = {}


def extract_features(upstroke_load, downstroke_load, pos_up):
    """Extract the 5 features used during training."""
    n = len(pos_up)
    pos_down = np.linspace(100, 0, n)
    load_full = np.concatenate([upstroke_load, downstroke_load])
    area = abs(np.trapezoid(upstroke_load, pos_up) +
               np.trapezoid(downstroke_load, pos_down))
    peak_load = np.max(load_full)
    min_load = np.min(load_full)
    load_range = peak_load - min_load
    fill_ratio = (np.mean(load_full) - min_load) / load_range if load_range > 0 else 0
    return [area, peak_load, min_load, load_range, fill_ratio], peak_load, min_load


def generate_dynacard(condition, W_r=4800, W_f=9800, n=50):
    """
    Kinematic pump model accounting for rod stretch and valve motion.
    Returns upstroke_loads, downstroke_loads, position array.
    """
    pos_up = np.linspace(0, 100, n)
    up = np.zeros(n)
    dn = np.zeros(n)

    if condition == "normal":
        up[:20] = np.linspace(W_r, W_r + W_f, 20)
        up[20:] = W_r + W_f + np.random.normal(0, 80, n - 20)
        dn[:20] = np.linspace(W_r + W_f, W_r, 20)
        dn[20:] = W_r + np.random.normal(0, 80, n - 20)

    elif condition == "rod_floating":
        up[:20] = np.linspace(W_r, W_r + W_f, 20)
        up[20:] = W_r + W_f + np.random.normal(0, 80, n - 20)
        dn[:35] = np.linspace(W_r + W_f, W_r + W_f * 0.55, 35)
        dn[35:] = W_r + W_f * 0.55 + np.random.normal(0, 80, n - 35)

    elif condition == "fluid_pound":
        up[:20] = np.linspace(W_r, W_r + W_f, 20)
        up[20:] = W_r + W_f + np.random.normal(0, 80, n - 20)
        dn[:12] = np.linspace(W_r + W_f, W_r + W_f * 0.95, 12)
        dn[12:18] = np.linspace(W_r + W_f * 0.95, W_r * 0.7, 6)
        dn[18:] = W_r + np.random.normal(0, 100, n - 18)

    return up, dn, pos_up


def compute_depth_profile(bottomhole_temp, phase, surface_ambient=28.0):
    """
    Compute wellbore temperature and viscosity gradient from surface to sandface (0 to 1200m).
    """
    depths = [0, 200, 400, 600, 800, 1000, 1150, 1200]
    points = []
    
    for z in depths:
        frac = z / 1200.0
        if phase == "Injection":
            # Wellhead is hottest during steam injection (~310°C), minor loss to sandface (~260°C)
            t_z = 310.0 - (310.0 - bottomhole_temp) * (frac ** 0.8)
        else:
            # During production, fluid cools as it rises from sandface to surface
            # Sandface is at bottomhole_temp, surface fluid arrives cooled
            t_z = surface_ambient + (bottomhole_temp - surface_ambient) * (frac ** 0.6)
            
        t_z = round(float(t_z), 1)
        v_z = round(float(calculate_viscosity(t_z)), 1)
        points.append({"depth_m": z, "temp_c": t_z, "visc_cp": v_z})
        
    return {
        "depth_points": points,
        "pump_depth_m": 1000.0,
        "perforations_top_m": 1150.0,
        "perforations_bottom_m": 1200.0
    }


def precompute_well(well_id, offset_hours, T_initial, T_reservoir, decline_tau, cycle_number, initial_bpd=130.0):
    """
    Multi-cycle CSS thermal recovery engine.
    Cycle 1 = Virgin (low water cut, high thermal response)
    Cycle 2 = Stable (moderate water cut)
    Cycle 4 = Mature/Depleted (high water cut, rapid heat loss, steam channeling risk)
    """
    steps = []
    sim_time = datetime.now()

    # Cycle degradation scaling
    cycle_oil_decay = max(0.45, 1.0 - (cycle_number - 1) * 0.18)
    water_cut_base = min(82.0, 28.0 + (cycle_number - 1) * 16.0)

    for step in range(180):
        hours_passed = (step + 1) * 2.8 + offset_hours
        sim_time += timedelta(hours=2.8)
        cycle_time = hours_passed % 504  # 504 hours = 21 days

        if cycle_time < 168:  # Injection Phase (7 days)
            phase = "Injection"
            T = T_initial
            spm = 0.0
            daily_oil = 0.0
            daily_steam = 60.0  # 60 tons/day steam injection
            sor = 0.0
            water_cut = 100.0
        elif cycle_time < 216:  # Soak Phase (2 days)
            phase = "Soak"
            T = T_initial
            spm = 0.0
            daily_oil = 0.0
            daily_steam = 0.0
            sor = 0.0
            water_cut = 100.0
        else:  # Production Phase (12 days)
            phase = "Production"
            cooling_days = (cycle_time - 216) / 24.0
            T = boberg_lantz_temperature_decline(T_initial, T_reservoir, cooling_days, decline_tau)
            spm = 6.5 if T > 90.0 else (5.0 if T > 70.0 else 3.8)
            
            # Darcy-correct relative productivity index (PI) ratio
            visc = calculate_viscosity(T)
            visc_at_steam_temp = calculate_viscosity(T_initial)
            visc_inflow_factor = min(1.0, visc_at_steam_temp / max(visc, 1.0))
            
            # Heavy oil recovery factor declines with cycle number (thermal exhaustion)
            effective_bpd = initial_bpd * cycle_oil_decay
            daily_oil = max(5.0, effective_bpd * visc_inflow_factor * 0.40)
            
            # Steam amortized over production days
            daily_steam = 420.0 / 12.0  # 35 tons/day
            sor = daily_steam / max(daily_oil, 0.1)
            water_cut = min(88.0, water_cut_base + (cooling_days / 12.0) * 8.0)

        visc = calculate_viscosity(T)

        # Physics-based regime mapping for dynacard state
        if phase != "Production":
            condition = "normal"
        elif visc > 2200.0:
            condition = "rod_floating"
        elif visc > 650.0:
            condition = "fluid_pound"
        else:
            condition = "normal"

        up, dn, pos_up = generate_dynacard(condition)
        features, peak_load, min_load = extract_features(up, dn, pos_up)

        # Downhole Gibbs Wave transformation
        downhole = compute_downhole_pump_card(up, dn, pos_up)

        # Real-time ML Inference
        proba = clf.predict_proba([features])[0]
        diag_idx = int(np.argmax(proba))
        diagnosis = clf.classes_[diag_idx]
        confidence = float(proba[diag_idx])

        # Economics calculations
        revenue = daily_oil * PPAC_INDIAN_CRUDE_BASKET_USD
        cost = daily_steam * EIA_STEAM_GENERATION_COST_USD
        margin = revenue - cost
        
        if phase == "Production" and sor > 0:
            rate_of_sor_rise = 0.15
            remaining_sor_headroom = max(0.0, ECONOMIC_CUTOFF_SOR - sor)
            days_to_cutoff = int(remaining_sor_headroom / rate_of_sor_rise)
        else:
            days_to_cutoff = 14

        pos_dn = np.linspace(100, 0, len(dn))
        card_area_joules = features[0] * 0.112985

        phase_day = round(float(max(0.0, (cycle_time % 168) / 24.0) if phase == 'Injection' else max(0.0, (cycle_time - 168) / 24.0) if phase == 'Soak' else max(0.0, (cycle_time - 216) / 24.0)), 1)
        tubing_psi = round(float(min(250.0, max(80.0, 90.0 + visc / 150.0))), 1)
        casing_psi = round(float(min(120.0, max(30.0, 45.0 + daily_oil * 0.25))), 1)

        wellbore_prof = compute_depth_profile(T, phase)

        steps.append({
            "timestamp": sim_time.isoformat(),
            "well_id": well_id,
            "load": round(float(peak_load), 1),
            "position": round(float(pos_up[-1]), 1),
            "temperature": round(float(T), 1),
            "viscosity": round(float(visc), 1),
            "spm": round(float(spm), 1),
            "diagnosis": diagnosis,
            "confidence": round(confidence, 3),
            "phase": phase,
            "cycle_number": cycle_number,
            "water_cut_pct": round(float(water_cut), 1),
            "phase_day": phase_day,
            "tubing_psi": tubing_psi,
            "casing_psi": casing_psi,
            "dynacard": {
                "surface_up": [{"pos": round(float(p), 1), "load": round(float(l), 1)} for p, l in zip(pos_up, up)],
                "surface_dn": [{"pos": round(float(p), 1), "load": round(float(l), 1)} for p, l in zip(pos_dn, dn)],
                "downhole_up": downhole["downhole_up"],
                "downhole_dn": downhole["downhole_dn"],
                "plunger_stroke_in": downhole["plunger_stroke_in"],
                "card_area_joules": round(float(card_area_joules), 1),
                "surface_peak_load": round(float(peak_load), 1),
                "surface_min_load": round(float(min_load), 1),
            },
            "economics": {
                "oil_price_usd_bbl": PPAC_INDIAN_CRUDE_BASKET_USD,
                "steam_cost_usd_ton": EIA_STEAM_GENERATION_COST_USD,
                "daily_oil_bpd": round(float(daily_oil), 1),
                "daily_steam_tons": round(float(daily_steam), 1),
                "current_sor": round(float(sor), 2),
                "economic_cutoff_sor": round(float(ECONOMIC_CUTOFF_SOR), 2),
                "net_daily_margin_usd": round(float(margin), 1),
                "days_to_sor_cutoff": max(0, days_to_cutoff)
            },
            "wellbore_profile": wellbore_prof
        })

    return steps


def compute_surface_facility_metrics(current_fleet_telemetry):
    """
    Coupled Surface Network Model:
    OTSG Boiler -> Trunk Steam Header -> Wellhead -> Flowline -> GGS Separator
    """
    total_oil = sum(w["economics"]["daily_oil_bpd"] for w in current_fleet_telemetry)
    total_steam_demand = sum(w["economics"]["daily_steam_tons"] for w in current_fleet_telemetry if w["phase"] == "Injection")
    
    # Central OTSG boiler load (300 t/d base capacity)
    boiler_rate = max(120.0, total_steam_demand + 45.0)  # +45 t/d distribution loss & standby
    boiler_fuel_gas = round(float((boiler_rate * 2.2) / 1000.0), 3) # ~0.85 MMSCFD
    
    # Flowline temperature drop modeling: T_ggs = T_amb + (T_wellhead - T_amb) * exp(-U*A / m*Cp)
    flowline_temps = {}
    gel_risk = {}
    
    for w in current_fleet_telemetry:
        wid = w["well_id"]
        # Surface wellhead temperature is approximately tubing head delivery
        t_wh = w["wellbore_profile"]["depth_points"][0]["temp_c"]
        # Flowline length 1.2km to GGS
        t_ggs = round(float(28.0 + (t_wh - 28.0) * math.exp(-0.45)), 1)
        flowline_temps[wid] = t_ggs
        
        # In heavy oil, below 42°C viscosity skyrockets past 5,000 cP causing line choking
        if t_ggs < 38.0:
            gel_risk[wid] = "CRITICAL_GEL_HAZARD"
        elif t_ggs < 48.0:
            gel_risk[wid] = "ELEVATED"
        else:
            gel_risk[wid] = "NORMAL"

    avg_wc = np.mean([w["water_cut_pct"] for w in current_fleet_telemetry])

    return {
        "boiler_steam_rate_tpd": round(float(boiler_rate), 1),
        "boiler_fuel_gas_mmscfd": boiler_fuel_gas,
        "boiler_thermal_eff_pct": 82.4,
        "steam_header_pressure_mpa": 16.2,
        "steam_header_temp_c": 348.5,
        "steam_quality_pct": 78.5,
        "total_field_oil_bpd": round(float(total_oil), 1),
        "total_field_water_cut_pct": round(float(avg_wc), 1),
        "flowline_gel_risk": gel_risk,
        "flowline_temps_c": flowline_temps
    }


def run_simulation():
    print("ILLUSTRATIVE - UNCALIBRATED (Generic Heavy-Oil Default Parameters)")
    print("Precomputing multi-cycle fleet with surface gathering network twin...")

    fleet = [
        precompute_well("BGW-01", offset_hours=240, T_initial=255.0, T_reservoir=40.0, decline_tau=42.0, cycle_number=2, initial_bpd=135.0), # Cycle 2: Established producer
        precompute_well("BGW-02", offset_hours=460, T_initial=240.0, T_reservoir=40.0, decline_tau=32.0, cycle_number=4, initial_bpd=95.0),  # Cycle 4: Mature / Choked / Watercut high
        precompute_well("BGW-03", offset_hours=40,  T_initial=260.0, T_reservoir=40.0, decline_tau=50.0, cycle_number=1, initial_bpd=155.0), # Cycle 1: Virgin injection
    ]

    print("Precomputation complete. Streaming real-time coupled Well-to-Surface telemetry...")

    step = 0
    try:
        while True:
            current_step_telemetry = []
            for well_data in fleet:
                payload = dict(well_data[step % 180])
                payload["timestamp"] = datetime.now().isoformat()
                current_step_telemetry.append(payload)
                try:
                    requests.post(API_URL, json=payload, timeout=1.5)
                except requests.exceptions.RequestException:
                    pass

            # Compute and broadcast coupled surface facility metrics
            surface_payload = compute_surface_facility_metrics(current_step_telemetry)
            try:
                requests.post(SURFACE_API_URL, json=surface_payload, timeout=1.5)
            except requests.exceptions.RequestException:
                pass

            step += 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("Simulation stopped.")


if __name__ == "__main__":
    run_simulation()
