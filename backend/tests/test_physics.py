import sys
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ml"))

from thermal_models import (
    calculate_viscosity,
    boberg_lantz_temperature_decline,
    marx_langenheim_heated_area,
    ramey_wellbore_heat_loss,
    compute_downhole_pump_card
)

def test_viscosity_baghewala_calibration():
    # 40°C (Reservoir datum): ~14,900 cP ± 5%
    v40 = calculate_viscosity(40.0)
    assert 14000.0 <= v40 <= 16000.0, f"Expected ~14,900 cP at 40°C, got {v40}"

    # 100°C (Mid-production): ~810 cP ± 10%
    v100 = calculate_viscosity(100.0)
    assert 700.0 <= v100 <= 950.0, f"Expected ~810 cP at 100°C, got {v100}"

    # 250°C (Steam saturation): ~10 cP ± 20%
    v250 = calculate_viscosity(250.0)
    assert 5.0 <= v250 <= 20.0, f"Expected ~10 cP at 250°C, got {v250}"


def test_boberg_lantz_temperature_decline():
    # At t=0, temperature equals initial steam temperature
    t0 = boberg_lantz_temperature_decline(255.0, 40.0, 0.0, 45.0)
    assert np.isclose(t0, 255.0), f"Expected 255°C at t=0, got {t0}"

    # As t -> infinity, temperature approaches reservoir temperature
    t_inf = boberg_lantz_temperature_decline(255.0, 40.0, 500.0, 45.0)
    assert np.isclose(t_inf, 40.0, atol=0.1), f"Expected ~40°C at t=500d, got {t_inf}"

    # Strictly monotonically decreasing with cooling days
    t1 = boberg_lantz_temperature_decline(255.0, 40.0, 5.0, 45.0)
    t2 = boberg_lantz_temperature_decline(255.0, 40.0, 10.0, 45.0)
    assert t1 > t2 > 40.0, f"Expected monotonic decline: {t1} > {t2}"


def test_marx_langenheim_heated_area():
    # At t=0, heated area is 0
    a0 = marx_langenheim_heated_area(420.0, 1050.0, 410.0, 0.0)
    assert a0 == 0.0, f"Expected 0 area at t=0, got {a0}"

    # At t=15 days, positive heated area
    a15 = marx_langenheim_heated_area(420.0, 1050.0, 410.0, 15.0)
    assert a15 > 1000.0, f"Expected substantial heated area at 15d, got {a15}"

    # Strictly monotonically increasing with injection time
    a5 = marx_langenheim_heated_area(420.0, 1050.0, 410.0, 5.0)
    a10 = marx_langenheim_heated_area(420.0, 1050.0, 410.0, 10.0)
    assert a15 > a10 > a5 > 0.0, "Heated zone must grow monotonically"


def test_downhole_pump_card_gibbs_lite():
    up = np.linspace(4800, 14600, 50)
    dn = np.linspace(14600, 4800, 50)
    pos = np.linspace(0, 100, 50)
    card = compute_downhole_pump_card(up, dn, pos, stroke_length_in=100.0)

    assert "downhole_up" in card
    assert "downhole_dn" in card
    assert "plunger_stroke_in" in card
    assert len(card["downhole_up"]) == 50
    assert len(card["downhole_dn"]) == 50
    # Plunger stroke should reflect elastic rod elongation recovery
    assert 85.0 <= card["plunger_stroke_in"] <= 100.0
