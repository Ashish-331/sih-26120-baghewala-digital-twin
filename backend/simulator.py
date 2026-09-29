import sys
import os
import time
import math
import random
import requests
import joblib
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Fix #1: Relative path resolution to repository root
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))

from thermal_models import (
    boberg_lantz_temperature_decline, 
    calculate_viscosity, 
    marx_langenheim_heated_area,
    compute_downhole_pump_card,
    ramey_wellbore_heat_loss
)

API_URL = os.getenv("TWIN_API_URL", "http://127.0.0.1:8000/api/telemetry")
SURFACE_API_URL = os.getenv("TWIN_SURFACE_API_URL", "http://127.0.0.1:8000/api/surface")
MODEL_PATH = Path(os.getenv("TWIN_MODEL_PATH", ROOT / "ml" / "dynacard_rf_classifier.pkl"))

# Fix #11: Ensure model exists
if not MODEL_PATH.exists():
    print(f"[SIMULATOR] Model missing at {MODEL_PATH}. Training 5-class Random Forest...")
    import subprocess
    subprocess.run([sys.executable, str(ROOT / "ml" / "train_classifier.py")], check=True)

# Load the trained ML classifier once at startup
clf = joblib.load(MODEL_PATH)
print(f"[SIMULATOR] Loaded ML classifier from {MODEL_PATH}")

# Benchmark economic constants from plan.md Section 4
PPAC_INDIAN_CRUDE_BASKET_USD = 76.50  # $/bbl
EIA_STEAM_GENERATION_COST_USD = 24.20 # $/ton (scaled for Indian domestic NG tariffs)
ECONOMIC_CUTOFF_SOR = PPAC_INDIAN_CRUDE_BASKET_USD / EIA_STEAM_GENERATION_COST_USD # ~3.16 tons/bbl


def extract_features(position, load):
    """
    7 handcrafted kinematic shape features matching train_classifier.py (Fix #8, #10).
    """
    half = len(load) // 2
    area = abs(np.trapezoid(load[:half], position[:half]) + np.trapezoid(load[half:], position[half:]))
    peak_load = np.max(load)
    min_load = np.min(load)
    load_range = max(1.0, peak_load - min_load)
    fill_ratio = (np.mean(load) - min_load) / load_range
    upstroke_slope = (load[half - 1] - load[20]) / max(1, half - 21)
    downstroke_midpoint_load = load[half + 15] / peak_load
    return [area, peak_load, min_load, load_range, fill_ratio, upstroke_slope, downstroke_midpoint_load], peak_load, min_load


def generate_dynacard(condition, W_r=4800, W_f=9800, n=50):
    """
    Kinematic pump model with domain perturbations for 5 standard fault classes.
    """
    pos_up = np.linspace(0, 100, n)
    up = np.zeros(n)
    dn = np.zeros(n)
    noise_scale = 80.0

    if condition == "normal":
        up[:20] = np.linspace(W_r, W_r + W_f, 20)
        up[20:] = W_r + W_f + np.random.normal(0, noise_scale, n - 20)
        dn[:20] = np.linspace(W_r + W_f, W_r, 20)
        dn[20:] = W_r + np.random.normal(0, noise_scale, n - 20)

    elif condition == "rod_floating":
        up[:20] = np.linspace(W_r, W_r + W_f, 20)
        up[20:] = W_r + W_f + np.random.normal(0, noise_scale, n - 20)
        dn[:35] = np.linspace(W_r + W_f, W_r + W_f * 0.58, 35)
        dn[35:] = W_r + W_f * 0.58 + np.random.normal(0, noise_scale, n - 35)

    elif condition == "fluid_pound":
        up[:20] = np.linspace(W_r, W_r + W_f, 20)
        up[20:] = W_r + W_f + np.random.normal(0, noise_scale, n - 20)
        dn[:12] = np.linspace(W_r + W_f, W_r + W_f * 0.92, 12)
        dn[12:18] = np.linspace(W_r + W_f * 0.92, W_r * 0.65, 6)
        dn[18:] = W_r + np.random.normal(0, noise_scale * 1.3, n - 18)

    elif condition == "gas_interference":
        up[:30] = np.linspace(W_r, W_r + W_f, 30) ** 0.95 * (W_r + W_f) ** 0.05
        up[30:] = W_r + W_f + np.random.normal(0, noise_scale, n - 30)
        dn[:25] = (W_r + W_f) - ((np.linspace(0, 1, 25) ** 1.8) * W_f)
        dn[25:] = W_r + np.random.normal(0, noise_scale, n - 25)

    elif condition == "traveling_valve_leak":
        up[:20] = np.linspace(W_r, W_r + W_f, 20)
        up[20:] = np.linspace(W_r + W_f, W_r + W_f * 0.72, n - 20) + np.random.normal(0, noise_scale, n - 20)
        dn[:20] = np.linspace(W_r + W_f * 0.72, W_r, 20)
        dn[20:] = W_r + np.random.normal(0, noise_scale, n - 20)

    return up, dn, pos_up


def compute_depth_profile(bottomhole_temp, phase, surface_ambient=28.0, injection_day=1.0):
    """
    Fix #7: Compute wellbore temperature profile using Ramey (1962) heat transmission model.
    """
    depths = [0, 200, 400, 600, 800, 1000, 1150, 1200]
    points = []
    
    for z in depths:
        if phase == "Injection":
            # Ramey analytical heat transmission formulation along injection tubing
            t_z = ramey_wellbore_heat_loss(depth_m=z, surface_injection_temp_c=310.0, geothermal_gradient_c_per_m=0.03, time_days=injection_day)
        else:
            # Production cooling gradient
            frac = z / 1200.0
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


def precompute_well(well_id, offset_hours, T_initial, T_reservoir, decline_tau, cycle_number, initial_bpd=135.0):
    """
    Multi-cycle CSS thermal recovery engine.
    Fixes: #7 (Marx-Langenheim/Ramey), #20 (softened inflow), #21 (dynamic slope), #23 (sim_time), #24 (water cut null outside prod)
    """
    steps = []
    sim_time = datetime.now()

    # Cycle degradation scaling
    cycle_oil_decay = max(0.50, 1.0 - (cycle_number - 1) * 0.16)
    water_cut_base = min(82.0, 28.0 + (cycle_number - 1) * 15.0)

    cum_steam = 0.0
    cum_oil = 0.0
    recent_sor_history = []

    for step in range(180):
        hours_passed = (step + 1) * 2.8 + offset_hours
        sim_time += timedelta(hours=2.8)
        cycle_time = hours_passed % 504  # 504 hours = 21 days

        heated_area_m2 = None
        heated_radius_m = None

        if cycle_time < 168:  # Injection Phase (7 days)
            phase = "Injection"
            T = T_initial
            spm = 0.0
            daily_oil = 0.0
            daily_steam = 60.0  # 60 tons/day steam injection
            cum_steam += daily_steam * (2.8 / 24.0)
            sor = 0.0
            water_cut = None  # Fix #24: None during non-production

            # Fix #7: Call Marx-Langenheim (1961) during injection!
            inj_days = (cycle_time / 24.0) + 0.1
            heated_area_m2 = round(float(marx_langenheim_heated_area(
                injection_rate_bpd=420.0,
                steam_enthalpy_btu_lb=1050.0,
                delta_T_f=410.0,
                time_days=inj_days,
                formation_thickness_ft=33.0
            )), 1)
            heated_radius_m = round(float(math.sqrt(heated_area_m2 / math.pi)), 1)

        elif cycle_time < 216:  # Soak Phase (2 days)
            phase = "Soak"
            T = T_initial
            spm = 0.0
            daily_oil = 0.0
            daily_steam = 0.0
            sor = 0.0
            water_cut = None  # Fix #24: None during soak
            
            # Heated area holds during soak
            heated_area_m2 = round(float(marx_langenheim_heated_area(
                injection_rate_bpd=420.0,
                steam_enthalpy_btu_lb=1050.0,
                delta_T_f=410.0,
                time_days=7.0,
                formation_thickness_ft=33.0
            )), 1)
            heated_radius_m = round(float(math.sqrt(heated_area_m2 / math.pi)), 1)

        else:  # Production Phase (12 days)
            phase = "Production"
            cooling_days = (cycle_time - 216) / 24.0
            T = boberg_lantz_temperature_decline(T_initial, T_reservoir, cooling_days, decline_tau)
            spm = 6.5 if T > 95.0 else (5.2 if T > 72.0 else 3.8)
            
            visc = calculate_viscosity(T)
            visc_at_steam_temp = calculate_viscosity(T_initial)
            
            # Fix #20: Soften inflow response so well does not prematurely collapse
            # Heavy oil PI responds sub-linearly to viscosity due to thermal gradient around wellbore
            visc_inflow_factor = min(1.0, (visc_at_steam_temp / max(visc, 1.0)) ** 0.5)
            
            effective_bpd = initial_bpd * cycle_oil_decay
            daily_oil = max(8.0, effective_bpd * visc_inflow_factor * 0.45)
            
            cum_oil += daily_oil * (2.8 / 24.0)
            daily_steam = 420.0 / 12.0  # 35 tons/day amortized
            sor = daily_steam / max(daily_oil, 0.1)
            water_cut = min(88.0, water_cut_base + (cooling_days / 12.0) * 8.0)
            
            recent_sor_history.append(sor)

        visc = calculate_viscosity(T)

        # Regimes
        if phase != "Production":
            condition = "normal"
        elif visc > 2400.0:
            condition = "rod_floating"
        elif visc > 700.0 and water_cut and water_cut > 60.0:
            condition = "fluid_pound"
        else:
            condition = "normal"

        up, dn, pos_up = generate_dynacard(condition)
        full_pos = np.concatenate([pos_up, np.linspace(100, 0, len(dn))])
        full_load = np.concatenate([up, dn])
        features, peak_load, min_load = extract_features(full_pos, full_load)

        # Downhole Gibbs Wave transformation
        downhole = compute_downhole_pump_card(up, dn, pos_up)

        # Real-time ML Inference
        proba = clf.predict_proba([features])[0]
        diag_idx = int(np.argmax(proba))
        confidence = float(proba[diag_idx])
        
        # Fix #12: Confidence thresholding (<0.70 becomes uncertain)
        if confidence < 0.70:
            diagnosis = "uncertain"
        else:
            diagnosis = clf.classes_[diag_idx]

        # Fix #20: Economics with both instantaneous and cumulative SOR
        cum_sor = round(float(cum_steam / max(cum_oil, 0.1)), 2)
        revenue = daily_oil * PPAC_INDIAN_CRUDE_BASKET_USD
        cost = daily_steam * EIA_STEAM_GENERATION_COST_USD
        margin = revenue - cost
        
        # Fix #21: Dynamic slope estimation from recent SOR trend
        if phase == "Production" and len(recent_sor_history) >= 3 and sor > 0:
            k = min(len(recent_sor_history), 8)
            y_pts = recent_sor_history[-k:]
            x_pts = list(range(len(y_pts)))
            slope = float(np.polyfit(x_pts, y_pts, 1)[0]) if len(y_pts) > 1 else 0.12
            slope = max(0.02, slope)
            remaining_sor = max(0.0, ECONOMIC_CUTOFF_SOR - sor)
            days_to_cutoff = int(remaining_sor / slope)
        else:
            days_to_cutoff = 14

        card_area_joules = features[0] * 0.112985

        phase_day = round(float(max(0.0, (cycle_time % 168) / 24.0) if phase == 'Injection' else max(0.0, (cycle_time - 168) / 24.0) if phase == 'Soak' else max(0.0, (cycle_time - 216) / 24.0)), 1)
        tubing_psi = round(float(min(250.0, max(80.0, 90.0 + visc / 150.0))), 1)
        casing_psi = round(float(min(120.0, max(30.0, 45.0 + daily_oil * 0.25))), 1)

        wellbore_prof = compute_depth_profile(T, phase, injection_day=phase_day)

        steps.append({
            "timestamp": datetime.now().isoformat(),  # Wall clock
            "sim_time": sim_time.isoformat(),          # Fix #23: Process clock (+2.8h/step)
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
            "water_cut_pct": round(float(water_cut), 1) if water_cut is not None else None,
            "phase_day": phase_day,
            "tubing_psi": tubing_psi,
            "casing_psi": casing_psi,
            "heated_zone_area_m2": heated_area_m2,
            "heated_radius_m": heated_radius_m,
            "dynacard": {
                "surface_up": [{"pos": round(float(p), 1), "load": round(float(l), 1)} for p, l in zip(pos_up, up)],
                "surface_dn": [{"pos": round(float(p), 1), "load": round(float(l), 1)} for p, l in zip(np.linspace(100, 0, len(dn)), dn)],
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
                "cumulative_sor": cum_sor,
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
    
    boiler_rate = max(120.0, total_steam_demand + 45.0)
    boiler_fuel_gas = round(float((boiler_rate * 2.2) / 1000.0), 3)
    
    flowline_temps = {}
    gel_risk = {}
    
    for w in current_fleet_telemetry:
        wid = w["well_id"]
        t_wh = w["wellbore_profile"]["depth_points"][0]["temp_c"]
        t_ggs = round(float(28.0 + (t_wh - 28.0) * math.exp(-0.45)), 1)
        flowline_temps[wid] = t_ggs
        
        if t_ggs < 38.0:
            gel_risk[wid] = "CRITICAL_GEL_HAZARD"
        elif t_ggs < 48.0:
            gel_risk[wid] = "ELEVATED"
        else:
            gel_risk[wid] = "NORMAL"

    active_wc = [w["water_cut_pct"] for w in current_fleet_telemetry if w["water_cut_pct"] is not None]
    avg_wc = np.mean(active_wc) if active_wc else 42.0

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
        precompute_well("BGW-01", offset_hours=240, T_initial=255.0, T_reservoir=40.0, decline_tau=42.0, cycle_number=2, initial_bpd=135.0),
        precompute_well("BGW-02", offset_hours=460, T_initial=240.0, T_reservoir=40.0, decline_tau=32.0, cycle_number=4, initial_bpd=95.0),
        precompute_well("BGW-03", offset_hours=40,  T_initial=260.0, T_reservoir=40.0, decline_tau=50.0, cycle_number=1, initial_bpd=155.0),
    ]

    print("Precomputation complete. Streaming real-time coupled Well-to-Surface telemetry (1 Hz deterministic replay)...")

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

            surface_payload = compute_surface_facility_metrics(current_step_telemetry)
            try:
                requests.post(SURFACE_API_URL, json=surface_payload, timeout=1.5)
            except requests.exceptions.RequestException:
                pass

            step += 1
            time.sleep(1) # Deterministic 1 Hz replay (Fix #4)
    except KeyboardInterrupt:
        print("Simulation stopped.")


if __name__ == "__main__":
    run_simulation()
