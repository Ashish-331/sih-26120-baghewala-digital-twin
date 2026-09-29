import sys
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from main import app

client = TestClient(app)

def test_api_status():
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "Baghewala" in data["system"]
    assert "SQLite" in data.get("persistence", "")


def test_api_surface():
    response = client.get("/api/surface")
    assert response.status_code == 200
    data = response.json()
    assert "boiler_steam_rate_tpd" in data
    assert "steam_header_pressure_mpa" in data
    assert "flowline_gel_risk" in data


def test_api_setpoint_actuation():
    payload = {
        "well_id": "BGW-01",
        "spm_override": 4.8,
        "auto_mode": False,
        "emergency_shutoff": False,
        "auth_token": "sih-26120-sec-token-baghewala"
    }
    response = client.post("/api/setpoint", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "accepted"
    assert data["command"]["spm_override"] == 4.8


def test_api_telemetry_ingest():
    sample_payload = {
        "timestamp": "2026-09-29T18:00:00Z",
        "sim_time": "2026-09-29T18:00:00Z",
        "well_id": "BGW-01",
        "load": 14500.0,
        "position": 100.0,
        "temperature": 180.0,
        "viscosity": 340.0,
        "spm": 6.5,
        "diagnosis": "normal",
        "confidence": 0.98,
        "phase": "Production",
        "cycle_number": 2,
        "water_cut_pct": 42.0,
        "phase_day": 4.2,
        "tubing_psi": 138.0,
        "casing_psi": 82.0
    }
    response = client.post("/api/telemetry", json=sample_payload)
    assert response.status_code == 201
    assert response.json()["status"] == "success"
