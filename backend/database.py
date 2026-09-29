import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional, Any

DB_PATH = Path(__file__).resolve().parent / "twin_data.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS telemetry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            sim_time TEXT,
            well_id TEXT,
            data_json TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            well_id TEXT,
            recommendation TEXT,
            sor REAL,
            data_json TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS surface_facility (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            data_json TEXT
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_well ON telemetry(well_id, id DESC)")
    conn.commit()
    conn.close()

def save_telemetry(well_id: str, timestamp: str, sim_time: str, data: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO telemetry (timestamp, sim_time, well_id, data_json) VALUES (?, ?, ?, ?)",
        (timestamp, sim_time, well_id, json.dumps(data))
    )
    conn.commit()
    conn.close()

def get_recent_history(limit_per_well: int = 60) -> Dict[str, List[dict]]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    wells = ["BGW-01", "BGW-02", "BGW-03"]
    history = {}
    for w in wells:
        cursor.execute(
            "SELECT data_json FROM telemetry WHERE well_id = ? ORDER BY id DESC LIMIT ?",
            (w, limit_per_well)
        )
        rows = cursor.fetchall()
        parsed = []
        for r in reversed(rows):
            d = json.loads(r[0])
            parsed.append({
                "timestamp": d.get("timestamp"),
                "sim_time": d.get("sim_time"),
                "temperature": d.get("temperature"),
                "viscosity": d.get("viscosity"),
                "load": d.get("load"),
                "sor": d.get("economics", {}).get("current_sor", 0.0) if d.get("economics") else 0.0,
                "cumulative_sor": d.get("economics", {}).get("cumulative_sor", 0.0) if d.get("economics") else 0.0,
                "daily_margin": d.get("economics", {}).get("net_daily_margin_usd", 0.0) if d.get("economics") else 0.0,
                "diagnosis": d.get("diagnosis", "normal")
            })
        history[w] = parsed
    conn.close()
    return history

def save_transition(alert: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transitions (timestamp, well_id, recommendation, sor, data_json) VALUES (?, ?, ?, ?, ?)",
        (alert.get("timestamp"), alert.get("well_id"), alert.get("recommendation"), alert.get("sor", 0.0), json.dumps(alert))
    )
    conn.commit()
    conn.close()

def get_recent_transitions(well_id: Optional[str] = None, limit: int = 50) -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if well_id:
        cursor.execute("SELECT data_json FROM transitions WHERE well_id = ? ORDER BY id DESC LIMIT ?", (well_id, limit))
    else:
        cursor.execute("SELECT data_json FROM transitions ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [json.loads(r[0]) for r in rows]

# Initialize tables on import
init_db()
