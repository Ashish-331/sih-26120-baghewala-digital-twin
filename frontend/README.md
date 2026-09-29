# PRAVAH (प्रवाह) — Industrial SCADA Frontend (SIH-26120)

Next.js 14 Industrial Supervisory Control and Data Acquisition (SCADA) Human-Machine Interface.

## Routes & Screens

- `/` — **Fleet Supervisory Overview:** Multi-cycle asset roster (Cycles 1, 2, 4) & Well-to-Surface pipeline topology.
- `/surface` — **Surface Facilities Twin:** Central OTSG-01 Steam Boiler telemetry & Thar Desert ambient temperature slider for bitumen gel hazard alerts.
- `/well/[id]` — **SCADA Wellbore Deep Dive:** Dual-trace Kinematic Dynacard (Hooke/Gibbs-Lite) vs Subsurface Wellbore Gradient $T(z)$, with closed-loop VFD setpoint control.
- `/analytics` — **AI Historian & SOR Optimizer:** Multi-well BHT decline curves & interactive Arps Hyperbolic economic breakeven calculator.

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | FastAPI backend REST endpoint base URL |
| `NEXT_PUBLIC_WS_URL` | `ws://127.0.0.1:8000/ws/telemetry` | Full-duplex WebSocket telemetry stream URL |
| `NEXT_PUBLIC_SETPOINT_TOKEN` | `sih-26120-sec-token-baghewala` | Security bearer token for VFD setpoint actuation |

## Quick Start

```bash
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000).
