from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import uvicorn
import json
from datetime import datetime

from models import (
    TelemetryData, 
    CycleTransition, 
    WellStatus, 
    SurfaceFacilityMetrics,
    SetPointCommand
)

app = FastAPI(
    title="SIH-26120 Digital Twin API",
    description="Coupled Well-to-Surface Digital Twin for Baghewala Heavy Oil CSS & SRP Operations. *ILLUSTRATIVE - UNCALIBRATED*",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores
telemetry_db: List[TelemetryData] = []
transition_db: List[CycleTransition] = []
fleet_status: Dict[str, WellStatus] = {}
well_history: Dict[str, List[dict]] = {"BGW-01": [], "BGW-02": [], "BGW-03": []}
surface_facility_state: Optional[dict] = None
active_setpoints: Dict[str, SetPointCommand] = {}
active_connections: List[WebSocket] = []


@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    # Send current fleet status, history, and surface metrics immediately on connect
    init_payload = {
        "type": "init",
        "fleet": {k: v.dict() for k, v in fleet_status.items()},
        "history": {k: v[-40:] for k, v in well_history.items()},
        "surface": surface_facility_state
    }
    try:
        await websocket.send_text(json.dumps(init_payload))
    except Exception:
        pass
        
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast(payload: dict):
    disconnected = []
    for conn in active_connections:
        try:
            await conn.send_text(json.dumps(payload))
        except Exception:
            disconnected.append(conn)
    for conn in disconnected:
        active_connections.remove(conn)


@app.post("/api/telemetry", status_code=201)
async def ingest_telemetry(data: TelemetryData):
    telemetry_db.append(data)
    
    econ = data.economics
    sor_val = econ.current_sor if econ else 0.0
    margin_val = econ.net_daily_margin_usd if econ else 0.0
    
    # Store in per-well rolling history
    if data.well_id not in well_history:
        well_history[data.well_id] = []
    well_history[data.well_id].append({
        "timestamp": data.timestamp,
        "temperature": data.temperature,
        "viscosity": data.viscosity,
        "load": data.load,
        "sor": sor_val,
        "daily_margin": margin_val,
        "diagnosis": data.diagnosis
    })
    if len(well_history[data.well_id]) > 200:
        well_history[data.well_id].pop(0)

    # Update fleet status for field overview
    fleet_status[data.well_id] = WellStatus(
        well_id=data.well_id,
        status=data.phase,
        temperature=data.temperature,
        viscosity=data.viscosity,
        phase=data.phase,
        cycle_number=data.cycle_number,
        water_cut_pct=data.water_cut_pct,
        diagnosis=data.diagnosis,
        last_seen=data.timestamp,
        sor=sor_val,
        daily_margin=margin_val
    )

    # SOR Economic Threshold Advisory (Milestone 3)
    alert = None
    if data.phase == "Production" and econ:
        if econ.current_sor >= econ.economic_cutoff_sor:
            if not transition_db or transition_db[-1].well_id != data.well_id or \
               transition_db[-1].recommendation != "Transition to Injection":
                loss_estimate = (econ.current_sor - econ.economic_cutoff_sor) * econ.daily_oil_bpd * econ.steam_cost_usd_ton
                alert = CycleTransition(
                    well_id=data.well_id,
                    current_phase="Production",
                    sor=econ.current_sor,
                    recommendation="Transition to Injection (Economic Breakeven Surpassed)",
                    timestamp=data.timestamp,
                    economic_loss_usd_day=round(loss_estimate, 1)
                )
                transition_db.append(alert)

    if len(telemetry_db) > 3000:
        telemetry_db.pop(0)

    # Broadcast to all WebSocket clients
    payload = {
        "type": "telemetry",
        "data": data.dict(),
        "fleet": {k: v.dict() for k, v in fleet_status.items()}
    }
    if alert:
        payload["alert"] = alert.dict()

    await broadcast(payload)
    return {"status": "success"}


@app.post("/api/surface", status_code=201)
async def ingest_surface_metrics(metrics: SurfaceFacilityMetrics):
    global surface_facility_state
    surface_facility_state = metrics.dict()
    await broadcast({
        "type": "surface",
        "data": surface_facility_state
    })
    return {"status": "success"}


@app.get("/api/surface")
async def get_surface():
    return surface_facility_state or {
        "boiler_steam_rate_tpd": 285.0,
        "boiler_fuel_gas_mmscfd": 0.825,
        "boiler_thermal_eff_pct": 82.4,
        "steam_header_pressure_mpa": 16.2,
        "steam_header_temp_c": 348.5,
        "steam_quality_pct": 78.5,
        "total_field_oil_bpd": 195.0,
        "total_field_water_cut_pct": 48.0,
        "flowline_gel_risk": {"BGW-01": "NORMAL", "BGW-02": "ELEVATED", "BGW-03": "NORMAL"},
        "flowline_temps_c": {"BGW-01": 52.4, "BGW-02": 41.2, "BGW-03": 78.0}
    }


@app.post("/api/setpoint")
async def update_setpoint(cmd: SetPointCommand):
    active_setpoints[cmd.well_id] = cmd
    await broadcast({
        "type": "setpoint_ack",
        "data": cmd.dict()
    })
    return {"status": "accepted", "command": cmd.dict()}


@app.get("/api/telemetry")
async def get_telemetry(well_id: str = None, limit: int = 100):
    data = telemetry_db[-limit:]
    if well_id:
        data = [d for d in data if d.well_id == well_id]
    return data


@app.get("/api/history")
async def get_history():
    return {k: v[-60:] for k, v in well_history.items()}


@app.get("/api/fleet")
async def get_fleet():
    return fleet_status


@app.get("/api/transitions")
async def get_transitions(well_id: str = None):
    data = transition_db[-50:]
    if well_id:
        data = [d for d in data if d.well_id == well_id]
    return data


@app.get("/api/status")
async def get_status():
    return {
        "status": "online",
        "system": "Well-to-Surface Digital Twin (SIH 26120)",
        "disclaimer": "ILLUSTRATIVE - UNCALIBRATED",
        "active_wells": list(fleet_status.keys()),
        "surface_network_online": surface_facility_state is not None,
        "active_ws_clients": len(active_connections)
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
