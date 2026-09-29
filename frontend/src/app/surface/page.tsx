"use client";

import { useEffect, useState, useRef } from "react";
import { BannerWatermark, Watermark } from "@/components/Watermark";
import { Flame, AlertTriangle, ShieldCheck, Layers } from "lucide-react";

import { API_URL, WS_URL } from "@/lib/config";

interface SurfaceMetrics {
  boiler_steam_rate_tpd: number;
  boiler_fuel_gas_mmscfd: number;
  boiler_thermal_eff_pct: number;
  steam_header_pressure_mpa: number;
  steam_header_temp_c: number;
  steam_quality_pct: number;
  total_field_oil_bpd: number;
  total_field_water_cut_pct: number;
  flowline_gel_risk: Record<string, string>;
  flowline_temps_c: Record<string, number>;
}

export default function SurfaceFacilities() {
  const [surface, setSurface] = useState<SurfaceMetrics>({
    boiler_steam_rate_tpd: 285.0,
    boiler_fuel_gas_mmscfd: 0.825,
    boiler_thermal_eff_pct: 82.4,
    steam_header_pressure_mpa: 16.2,
    steam_header_temp_c: 348.5,
    steam_quality_pct: 78.5,
    total_field_oil_bpd: 195.0,
    total_field_water_cut_pct: 48.0,
    flowline_gel_risk: { "BGW-01": "NORMAL", "BGW-02": "ELEVATED", "BGW-03": "NORMAL" },
    flowline_temps_c: { "BGW-01": 52.4, "BGW-02": 41.2, "BGW-03": 78.0 },
  });
  const [ambientTemp, setAmbientTemp] = useState<number>(28); // Thar Desert ambient
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Initial fetch from REST API
    fetch(`${API_URL}/api/surface`)
      .then((r) => r.json())
      .then((d) => { if (d) setSurface(d); })
      .catch(() => {});

    function connect() {
      wsRef.current = new WebSocket(WS_URL);
      wsRef.current.onopen = () => setConnected(true);
      wsRef.current.onclose = () => {
        setConnected(false);
        setTimeout(connect, 2000);
      };
      wsRef.current.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "surface" && payload.data) {
            setSurface(payload.data);
          } else if (payload.type === "init" && payload.surface) {
            setSurface(payload.surface);
          }
        } catch {
          // ignore
        }
      };
    }
    connect();
    return () => wsRef.current?.close();
  }, []);

  // Compute Thar desert ambient cooling impact on flowline delivery
  const adjustedFlowlineTemps: Record<string, number> = {};
  const adjustedGelRisk: Record<string, string> = {};

  Object.entries(surface.flowline_temps_c || {}).forEach(([wid, baseT]) => {
    // Delta shift based on ambient slider relative to standard 28°C
    const effT = Math.round((baseT + (ambientTemp - 28) * 0.45) * 10) / 10;
    adjustedFlowlineTemps[wid] = effT;
    if (effT < 38.0) {
      adjustedGelRisk[wid] = "CRITICAL_GEL_HAZARD";
    } else if (effT < 48.0) {
      adjustedGelRisk[wid] = "ELEVATED";
    } else {
      adjustedGelRisk[wid] = "NORMAL";
    }
  });

  return (
    <main className="min-h-screen bg-black flex flex-col font-mono text-zinc-300 relative select-none">
      <BannerWatermark />
      <Watermark />

      <header className="h-10 border-b border-zinc-800 bg-black px-6 flex justify-between items-center shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-[11px] tracking-widest font-bold text-zinc-100 uppercase">
            PRAVAH // SURFACE FACILITIES &amp; GATHERING NETWORK TWIN
          </h1>
          <span className="text-[8px] text-zinc-500 uppercase px-1.5 py-0.5 bg-zinc-900 border border-zinc-800">
            Baghewala Field Central Facilities
          </span>
        </div>
        <div className="flex items-center gap-4 text-[9px] uppercase tracking-widest text-zinc-500">
          <span className={`w-1.5 h-1.5 rounded-none ${connected ? "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.8)]" : "bg-red-600 animate-pulse"}`} />
          <span>OTSG-1 Boiler: <strong className="text-green-400">ONLINE (82.4% EFF)</strong></span>
          <span>GGS Separator: <strong className="text-cyan-400">ACTIVE</strong></span>
        </div>
      </header>

      <div className="p-5 flex flex-col gap-5 max-w-6xl w-full mx-auto">
        
        {/* Row 1: Central Steam Plant (OTSG Boiler) KPIs */}
        <div className="border border-zinc-800 bg-zinc-950 p-4">
          <div className="flex justify-between items-center border-b border-zinc-850 pb-2 mb-3">
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-amber-500" />
              <h2 className="text-[10px] text-zinc-350 uppercase tracking-widest font-bold">
                Central Once-Through Steam Generator (OTSG-01)
              </h2>
            </div>
            <span className="text-[8px] text-zinc-600">Rated Capacity: 300 Tons/Day • Natural Gas Fired</span>
          </div>

          <div className="grid grid-cols-6 gap-3 text-xs font-mono">
            <div className="bg-black p-2.5 border border-zinc-850">
              <span className="text-zinc-600 block text-[8px] uppercase">Steam Rate</span>
              <span className="text-lg font-bold text-cyan-400">
                {surface.boiler_steam_rate_tpd} <span className="text-xs text-zinc-500 font-normal">t/d</span>
              </span>
            </div>
            <div className="bg-black p-2.5 border border-zinc-850">
              <span className="text-zinc-600 block text-[8px] uppercase">Header Pressure</span>
              <span className="text-lg font-bold text-zinc-100">
                {surface.steam_header_pressure_mpa} <span className="text-xs text-zinc-500 font-normal">MPa</span>
              </span>
            </div>
            <div className="bg-black p-2.5 border border-zinc-850">
              <span className="text-zinc-600 block text-[8px] uppercase">Header Temp</span>
              <span className="text-lg font-bold text-amber-400">
                {surface.steam_header_temp_c}°C
              </span>
            </div>
            <div className="bg-black p-2.5 border border-zinc-850">
              <span className="text-zinc-600 block text-[8px] uppercase">Steam Quality</span>
              <span className="text-lg font-bold text-zinc-100">
                {surface.steam_quality_pct}%
              </span>
            </div>
            <div className="bg-black p-2.5 border border-zinc-850">
              <span className="text-zinc-600 block text-[8px] uppercase">Fuel Gas Rate</span>
              <span className="text-lg font-bold text-zinc-100">
                {surface.boiler_fuel_gas_mmscfd} <span className="text-xs text-zinc-500 font-normal">MMSCFD</span>
              </span>
            </div>
            <div className="bg-black p-2.5 border border-zinc-850">
              <span className="text-zinc-600 block text-[8px] uppercase">Thermal Eff.</span>
              <span className="text-lg font-bold text-green-400">
                {surface.boiler_thermal_eff_pct}%
              </span>
            </div>
          </div>
        </div>

        {/* Row 2: Interactive Gathering Network & Flowline Solidification Twin */}
        <div className="border border-zinc-800 bg-zinc-950 p-4 flex flex-col gap-4">
          <div className="flex justify-between items-center border-b border-zinc-850 pb-2">
            <div>
              <h2 className="text-[10px] text-zinc-350 uppercase tracking-widest font-bold">
                Surface Gathering Network &amp; Heavy Oil Flowline Gel Hazard
              </h2>
              <span className="text-[8px] text-zinc-600 block">
                Coupled heat-loss model along 1.2km insulated surface flowlines to Baghewala GGS
              </span>
            </div>

            {/* Ambient Thar desert temperature scenario slider */}
            <div className="flex items-center gap-3 bg-black px-3 py-1.5 border border-zinc-850">
              <span className="text-[9px] text-zinc-400 uppercase">Thar Desert Ambient:</span>
              <input
                type="range"
                min="5"
                max="48"
                value={ambientTemp}
                onChange={(e) => setAmbientTemp(Number(e.target.value))}
                className="w-24 accent-amber-500 cursor-pointer"
              />
              <span className="text-amber-400 font-bold text-xs">{ambientTemp}°C</span>
              <span className="text-[8px] text-zinc-600">
                {ambientTemp < 15 ? "(Winter Night)" : ambientTemp > 40 ? "(Summer Peak)" : "(Normal)"}
              </span>
            </div>
          </div>

          {/* Network Flowline Topology Layout */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {["BGW-01", "BGW-02", "BGW-03"].map((wid) => {
              const deliveryT = adjustedFlowlineTemps[wid] ?? 45.0;
              const risk = adjustedGelRisk[wid] ?? "NORMAL";
              const isCrit = risk === "CRITICAL_GEL_HAZARD";
              const isElev = risk === "ELEVATED";

              return (
                <div
                  key={wid}
                  className={`p-3 border bg-black flex flex-col justify-between ${
                    isCrit ? "border-red-700 shadow-[0_0_10px_rgba(239,68,68,0.25)]" :
                    isElev ? "border-amber-700" : "border-zinc-850"
                  }`}
                >
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <span className="text-[9px] text-zinc-500 uppercase block">Flowline Segment</span>
                      <span className="text-sm font-bold text-zinc-100">{wid} → GGS Header</span>
                    </div>
                    <span
                      className={`text-[8px] px-1.5 py-0.5 border uppercase font-bold tracking-wider ${
                        isCrit ? "bg-red-950 text-red-400 border-red-700 animate-pulse" :
                        isElev ? "bg-amber-950 text-amber-400 border-amber-700" :
                        "bg-green-950 text-green-400 border-green-800"
                      }`}
                    >
                      {risk.replace("_", " ")}
                    </span>
                  </div>

                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-zinc-500 text-[9px]">GGS Delivery Temp:</span>
                      <span className={`font-bold ${isCrit ? "text-red-400" : isElev ? "text-amber-400" : "text-zinc-200"}`}>
                        {deliveryT}°C
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500 text-[9px]">Bitumen Flowline Viscosity:</span>
                      <span className="text-zinc-300 font-mono">
                        {Math.round(1.84e-4 * Math.exp(5704 / (deliveryT + 273.15))).toLocaleString()} cP
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-500 text-[9px]">Line Length / Insulation:</span>
                      <span className="text-zinc-400">1,200m • 2&quot; Polyurethane</span>
                    </div>
                  </div>

                  {isCrit ? (
                    <div className="mt-2.5 pt-2 border-t border-red-900/60 text-[9px] text-red-400 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>CRITICAL: Cold Thar night temperature causing flowline bitumen gelling. Activate steam trace heating immediately!</span>
                    </div>
                  ) : isElev ? (
                    <div className="mt-2.5 pt-2 border-t border-amber-900/60 text-[9px] text-amber-400 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>ELEVATED: High pipeline frictional pressure drop. Monitor diluent injection.</span>
                    </div>
                  ) : (
                    <div className="mt-2.5 pt-2 border-t border-zinc-900 text-[9px] text-green-400 flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 shrink-0" />
                      <span>Flowline temperature above pour point. Free flowing emulsion.</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Row 3: Group Gathering Station (GGS) Separator & Field Totals */}
        <div className="border border-zinc-800 bg-zinc-950 p-4">
          <div className="flex justify-between items-center border-b border-zinc-850 pb-2 mb-3">
            <div className="flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              <h2 className="text-[10px] text-zinc-350 uppercase tracking-widest font-bold">
                Group Gathering Station (GGS Baghewala) — Inlet Manifold
              </h2>
            </div>
            <span className="text-[8px] text-zinc-600">Two-Phase Test Separator • Heated Emulsion Treater</span>
          </div>

          <div className="grid grid-cols-4 gap-4 text-xs">
            <div className="bg-black p-3 border border-zinc-850">
              <span className="text-zinc-600 block text-[8px] uppercase">Aggregated Heavy Oil Delivery</span>
              <span className="text-xl font-bold text-green-400">
                {surface.total_field_oil_bpd} <span className="text-xs text-zinc-500 font-normal">BPD</span>
              </span>
              <span className="text-[8px] text-zinc-500 block mt-1">9-12° API Bitumen Net Production</span>
            </div>

            <div className="bg-black p-3 border border-zinc-850">
              <span className="text-zinc-600 block text-[8px] uppercase">Average Field Water Cut</span>
              <span className="text-xl font-bold text-amber-400">
                {surface.total_field_water_cut_pct}%
              </span>
              <span className="text-[8px] text-zinc-500 block mt-1">Condensed steam return + formation water</span>
            </div>

            <div className="bg-black p-3 border border-zinc-850">
              <span className="text-zinc-600 block text-[8px] uppercase">Emulsion Treater Status</span>
              <span className="text-xl font-bold text-cyan-400">
                72.0°C <span className="text-xs text-zinc-500 font-normal">OPERATING</span>
              </span>
              <span className="text-[8px] text-zinc-500 block mt-1">Demulsifier injection rate: 45 ppm</span>
            </div>

            <div className="bg-black p-3 border border-zinc-850">
              <span className="text-zinc-600 block text-[8px] uppercase">Clean Oil Storage Stock</span>
              <span className="text-xl font-bold text-zinc-100">
                3,420 <span className="text-xs text-zinc-500 font-normal">BBL</span>
              </span>
              <span className="text-[8px] text-zinc-500 block mt-1">Tank Farm Capacity: 10,000 BBL</span>
            </div>
          </div>
        </div>

      </div>
    </main>
  );
}
