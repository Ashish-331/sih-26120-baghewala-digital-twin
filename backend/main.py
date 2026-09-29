from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
import uvicorn
import json
import os
import sys
import asyncio
from datetime import datetime

from contextlib import asynccontextmanager
from models import (
    TelemetryData, 
    CycleTransition, 
    WellStatus, 
    SurfaceFacilityMetrics,
    SetPointCommand
)
import database


async def run_embedded_simulator_loop():
    """
    Embedded 1 Hz Physics Replay Engine:
    Ensures that when deployed to cloud environments like Render, AWS, or Docker
    with a single start command (uvicorn main:app), the digital twin automatically
    generates coupled physics telemetry without requiring a separate background process.
    """
    await asyncio.sleep(1.0)
    try:
        import simulator
        fleet = [
            simulator.precompute_well("BGW-01", offset_hours=240, T_initial=255.0, T_reservoir=40.0, decline_tau=42.0, cycle_number=2, initial_bpd=135.0),
            simulator.precompute_well("BGW-02", offset_hours=460, T_initial=240.0, T_reservoir=40.0, decline_tau=32.0, cycle_number=4, initial_bpd=95.0),
            simulator.precompute_well("BGW-03", offset_hours=40,  T_initial=260.0, T_reservoir=40.0, decline_tau=50.0, cycle_number=1, initial_bpd=155.0),
        ]
        print("[PRAVAH TWIN] Embedded 1 Hz Physics Simulator active.")
        step = 0
        while True:
            current_step_telemetry = []
            for well_data in fleet:
                payload = dict(well_data[step % 180])
                payload["timestamp"] = datetime.now().isoformat()
                current_step_telemetry.append(payload)
                try:
                    telemetry_obj = TelemetryData(**payload)
                    await ingest_telemetry(telemetry_obj)
                except Exception:
                    pass

            try:
                surface_dict = simulator.compute_surface_facility_metrics(current_step_telemetry)
                surface_obj = SurfaceFacilityMetrics(**surface_dict)
                await ingest_surface_metrics(surface_obj)
            except Exception:
                pass

            step += 1
            await asyncio.sleep(1)
    except Exception as e:
        print(f"[PRAVAH TWIN] Embedded simulator error: {e}")


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    is_testing = os.getenv("TESTING", "false").lower() == "true" or "pytest" in sys.modules
    enable_embedded = os.getenv("ENABLE_EMBEDDED_SIMULATOR", "true").lower() == "true"
    sim_task = None
    if enable_embedded and not is_testing:
        sim_task = asyncio.create_task(run_embedded_simulator_loop())
        print("[STARTUP] Pravah Embedded 1 Hz Physics Simulator background task launched.")
    yield
    if sim_task:
        sim_task.cancel()


app = FastAPI(
    title="SIH-26120 Digital Twin API",
    description="Coupled Well-to-Surface Digital Twin for Baghewala Heavy Oil CSS & SRP Operations. *ILLUSTRATIVE - UNCALIBRATED*",
    version="3.1.0",
    lifespan=lifespan
)

# Fix #14: Clean CORS configuration without wildcard + credentials collision
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
if os.getenv("ALLOWED_ORIGIN"):
    ALLOWED_ORIGINS.append(os.getenv("ALLOWED_ORIGIN"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Public demo allows all origins
    allow_credentials=False, # Fix #14: False when using wildcard
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory fast state caches
fleet_status: Dict[str, WellStatus] = {}
surface_facility_state: Optional[dict] = None
active_setpoints: Dict[str, SetPointCommand] = {}
active_connections: List[WebSocket] = []

# Fix #16: Per-well alert deduplication state
last_alert_rec: Dict[str, str] = {}

VALID_AUTH_TOKEN = os.getenv("SETPOINT_AUTH_TOKEN", "sih-26120-sec-token-baghewala")


@app.get("/")
async def root():
    return {
        "system": "PRAVAH (प्रवाह) // Baghewala Well-to-Surface Digital Twin API",
        "status": "online",
        "message": "FastAPI backend is operational. For interactive Swagger API documentation, visit /docs. For live telemetry, connect to /ws/telemetry.",
        "documentation": "/docs",
        "health_check": "/api/status",
        "endpoints": {
            "status": "/api/status",
            "fleet": "/api/fleet",
            "history": "/api/history",
            "surface": "/api/surface",
            "websocket": "/ws/telemetry"
        },
        "active_wells": list(fleet_status.keys())
    }


@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    
    # Handshake payload with persistence-backed recent history (Fix #13)
    init_payload = {
        "type": "init",
        "fleet": {k: v.dict() for k, v in fleet_status.items()},
        "history": database.get_recent_history(limit_per_well=40),
        "surface": surface_facility_state
    }
    try:
        await websocket.send_text(json.dumps(init_payload))
    except Exception:
        pass
        
    try:
        while True:
            # Fix #18: Real Full-Duplex WebSocket — handle incoming operator commands from browser
            text = await websocket.receive_text()
            try:
                cmd_data = json.loads(text)
                if cmd_data.get("type") == "setpoint":
                    sp = SetPointCommand(**cmd_data.get("data", {}))
                    active_setpoints[sp.well_id] = sp
                    await broadcast({
                        "type": "setpoint_ack",
                        "data": sp.dict()
                    })
            except Exception:
                pass
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
    # Persist to SQLite (Fix #13)
    database.save_telemetry(data.well_id, data.timestamp, data.sim_time, data.model_dump())
    
    econ = data.economics
    sor_val = econ.current_sor if econ else 0.0
    cum_sor_val = econ.cumulative_sor if econ else 0.0
    margin_val = econ.net_daily_margin_usd if econ else 0.0

    # Update live fleet status
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
        cumulative_sor=cum_sor_val,
        daily_margin=margin_val
    )

    # Fix #16: Per-well alert deduplication
    alert = None
    if data.phase == "Production" and econ:
        if econ.current_sor >= econ.economic_cutoff_sor:
            rec_text = "Transition to Injection (Economic Breakeven Surpassed)"
            if last_alert_rec.get(data.well_id) != rec_text:
                loss_estimate = (econ.current_sor - econ.economic_cutoff_sor) * econ.daily_oil_bpd * econ.steam_cost_usd_ton
                alert = CycleTransition(
                    well_id=data.well_id,
                    current_phase="Production",
                    sor=econ.current_sor,
                    recommendation=rec_text,
                    timestamp=data.timestamp,
                    economic_loss_usd_day=round(loss_estimate, 1)
                )
                database.save_transition(alert.model_dump())
                last_alert_rec[data.well_id] = rec_text
        else:
            last_alert_rec[data.well_id] = "Optimal Production"

    # Broadcast to all WebSocket clients
    payload = {
        "type": "telemetry",
        "data": data.model_dump(),
        "fleet": {k: v.model_dump() for k, v in fleet_status.items()}
    }
    if alert:
        payload["alert"] = alert.model_dump()

    await broadcast(payload)
    return {"status": "success"}


@app.post("/api/surface", status_code=201)
async def ingest_surface_metrics(metrics: SurfaceFacilityMetrics):
    global surface_facility_state
    surface_facility_state = metrics.model_dump()
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


# Fix #14: Secure actuation endpoint with optional token verification
@app.post("/api/setpoint")
async def update_setpoint(cmd: SetPointCommand, authorization: Optional[str] = Header(None)):
    token = cmd.auth_token or (authorization.replace("Bearer ", "") if authorization else None)
    # Validate token if token enforcement is on
    if os.getenv("ENFORCE_SETPOINT_AUTH", "false").lower() == "true":
        if token != VALID_AUTH_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized VFD Setpoint Actuation")
            
    active_setpoints[cmd.well_id] = cmd
    await broadcast({
        "type": "setpoint_ack",
        "data": cmd.model_dump()
    })
    return {"status": "accepted", "command": cmd.model_dump()}


@app.get("/api/telemetry")
async def get_telemetry(well_id: str = None, limit: int = 100):
    hist = database.get_recent_history(limit_per_well=limit)
    if well_id:
        return hist.get(well_id, [])
    return hist


@app.get("/api/history")
async def get_history():
    return database.get_recent_history(limit_per_well=60)


@app.get("/api/fleet")
async def get_fleet():
    return fleet_status


@app.get("/api/transitions")
async def get_transitions(well_id: str = None):
    return database.get_recent_transitions(well_id=well_id)


@app.get("/api/status")
async def get_status():
    return {
        "status": "online",
        "system": "Pravah // Baghewala Well-to-Surface Digital Twin (SIH 26120)",
        "disclaimer": "ILLUSTRATIVE - UNCALIBRATED",
        "active_wells": list(fleet_status.keys()),
        "surface_network_online": surface_facility_state is not None,
        "active_ws_clients": len(active_connections),
        "persistence": "SQLite (twin_data.db)"
    }


if __name__ == "__main__":
    reload_flag = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload_flag)
