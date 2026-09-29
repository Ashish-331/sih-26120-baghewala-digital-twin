"use client";

import { useEffect, useState, useRef } from "react";
import { BannerWatermark, Watermark } from "@/components/Watermark";
import Link from "next/link";
import { Flame, Layers, GitCommit, ArrowRight } from "lucide-react";

import { API_URL, WS_URL } from "@/lib/config";

interface WellStatus {
  well_id: string;
  status: string;
  temperature: number;
  viscosity?: number;
  phase: string;
  cycle_number?: number;
  water_cut_pct?: number | null;
  diagnosis: string;
  last_seen: string;
  sor?: number;
  cumulative_sor?: number;
  daily_margin?: number;
}

const DIAGNOSIS_SEVERITY: Record<string, { label: string; style: string }> = {
  normal: { label: "NORMAL", style: "text-green-400 border-green-800 bg-green-950/20" },
  rod_floating: { label: "ROD FLOATING", style: "text-amber-400 border-amber-800 bg-amber-950/20" },
  fluid_pound: { label: "FLUID POUND", style: "text-red-400 border-red-800 bg-red-950/20" },
  gas_interference: { label: "GAS INTERFERENCE", style: "text-purple-400 border-purple-800 bg-purple-950/20" },
  traveling_valve_leak: { label: "VALVE LEAK", style: "text-pink-400 border-pink-800 bg-pink-950/20" },
  uncertain: { label: "UNCERTAIN (CONF < 70%)", style: "text-zinc-400 border-zinc-700 bg-zinc-900/40" },
};

const PHASE_COLOR: Record<string, string> = {
  Injection: "text-cyan-400",
  Soak: "text-purple-400",
  Production: "text-green-400",
};

export default function FieldOverview() {
  const [fleet, setFleet] = useState<Record<string, WellStatus>>({
    "BGW-01": { well_id: "BGW-01", status: "Production", temperature: 185.0, viscosity: 320.0, phase: "Production", cycle_number: 2, water_cut_pct: 42.0, diagnosis: "normal", last_seen: "", sor: 1.8, daily_margin: 2450 },
    "BGW-02": { well_id: "BGW-02", status: "Production", temperature: 72.0, viscosity: 2800.0, phase: "Production", cycle_number: 4, water_cut_pct: 78.0, diagnosis: "rod_floating", last_seen: "", sor: 4.2, daily_margin: -320 },
    "BGW-03": { well_id: "BGW-03", status: "Injection", temperature: 260.0, viscosity: 9.0, phase: "Injection", cycle_number: 1, water_cut_pct: null, diagnosis: "normal", last_seen: "", sor: 0.0, daily_margin: -850 },
  });
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/api/fleet`)
      .then((res) => res.json())
      .then((data) => {
        if (data && Object.keys(data).length > 0) setFleet(data);
      })
      .catch(() => {});

    function connect() {
      wsRef.current = new WebSocket(WS_URL);
      wsRef.current.onopen = () => setConnected(true);
      wsRef.current.onclose = () => {
        setConnected(false);
        setTimeout(connect, 2000);
      };
      wsRef.current.onerror = () => wsRef.current?.close();
      wsRef.current.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.fleet) {
            setFleet(payload.fleet);
          }
        } catch {
          // ignore
        }
      };
    }
    connect();
    return () => wsRef.current?.close();
  }, []);

  const wells = Object.values(fleet);
  const totalMargin = wells.reduce((acc, w) => acc + (w.daily_margin || 0), 0);

  return (
    <main className="min-h-screen bg-black flex flex-col font-mono text-zinc-300 relative select-none">
      <BannerWatermark />
      <Watermark />

      <header className="h-10 border-b border-zinc-800 bg-black px-6 flex justify-between items-center shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-[11px] tracking-widest font-bold text-zinc-100 uppercase">
            PRAVAH // BAGHEWALA FIELD — FLEET &amp; SURFACE NETWORK
          </h1>
          <span className="text-[8px] text-zinc-500 uppercase px-1.5 py-0.5 bg-zinc-900 border border-zinc-800">
            Oil India Ltd. Heavy Oil Asset • Jodhpur Sandstone
          </span>
        </div>
        <div className="flex items-center gap-3 text-[9px] uppercase tracking-widest">
          <span className={`w-1.5 h-1.5 rounded-none ${connected ? "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.8)]" : "bg-red-600 animate-pulse"}`} />
          <span className={connected ? "text-green-500" : "text-red-500"}>
            {connected ? "TELEMETRY SYNCHRONIZED" : "OFFLINE / RECONNECTING"}
          </span>
        </div>
      </header>

      <div className="p-5 flex flex-col gap-4 max-w-6xl w-full mx-auto">
        
        {/* Fleet KPI Executive Summary */}
        <div className="grid grid-cols-4 border border-zinc-800 divide-x divide-zinc-800 bg-black">
          <div className="p-3">
            <span className="text-[8px] text-zinc-600 uppercase tracking-widest block mb-0.5">Active Wells</span>
            <span className="text-xl font-bold text-zinc-100">{wells.length || 3}</span>
            <span className="text-[9px] text-zinc-500 block mt-0.5">Heavy Oil Producers</span>
          </div>
          <div className="p-3">
            <span className="text-[8px] text-zinc-600 uppercase tracking-widest block mb-0.5">Fleet Net Margin</span>
            <span className={`text-xl font-bold ${totalMargin >= 0 ? "text-green-400" : "text-red-400"}`}>
              ${Math.round(totalMargin).toLocaleString()}
              <span className="text-[9px] text-zinc-500 font-normal">/day</span>
            </span>
            <span className="text-[9px] text-zinc-500 block mt-0.5">PPAC Indian Netback ($76.5)</span>
          </div>
          <div className="p-3">
            <span className="text-[8px] text-zinc-600 uppercase tracking-widest block mb-0.5">Thermal Anomaly Flags</span>
            <span className={`text-xl font-bold ${wells.filter(w => w.diagnosis && w.diagnosis !== "normal").length > 0 ? "text-amber-400" : "text-zinc-400"}`}>
              {wells.filter(w => w.diagnosis && w.diagnosis !== "normal").length}
            </span>
            <span className="text-[9px] text-zinc-500 block mt-0.5">Rod Float / Fluid Pound</span>
          </div>
          <div className="p-3">
            <span className="text-[8px] text-zinc-600 uppercase tracking-widest block mb-0.5">Central Steam OTSG-1</span>
            <span className="text-xl font-bold text-cyan-400">285 <span className="text-[10px] text-zinc-500 font-normal">t/d</span></span>
            <span className="text-[9px] text-zinc-500 block mt-0.5">Header: 16.2 MPa @ 348°C</span>
          </div>
        </div>

        {/* Spatial SCADA Field Layout / Pipeline Network Diagram */}
        <div className="border border-zinc-800 bg-zinc-950 p-4">
          <div className="flex justify-between items-center border-b border-zinc-850 pb-2 mb-3">
            <div className="flex items-center gap-2">
              <GitCommit className="w-3.5 h-3.5 text-zinc-400" />
              <h2 className="text-[10px] text-zinc-350 uppercase tracking-widest font-bold">
                Well-to-Surface Topology &amp; Steam Distribution Loop
              </h2>
            </div>
            <Link href="/surface" className="text-[9px] text-cyan-400 hover:text-cyan-300 uppercase tracking-wider flex items-center gap-1">
              View Surface Facilities Twin <ArrowRight className="w-3 h-3" />
            </Link>
          </div>

          <div className="grid grid-cols-12 gap-3 items-center text-xs">
            {/* Central Steam Plant (Left Node) */}
            <div className="col-span-3 bg-black p-3 border border-zinc-850 flex flex-col gap-1">
              <div className="flex items-center gap-1.5 text-amber-400 text-[10px] font-bold">
                <Flame className="w-3.5 h-3.5" /> OTSG Boiler Plant
              </div>
              <span className="text-[9px] text-zinc-500">285 t/d Steam • 16.2 MPa</span>
              <div className="w-full bg-cyan-950 h-1 mt-1"><div className="w-full bg-cyan-400 h-full"></div></div>
              <span className="text-[8px] text-cyan-400 uppercase mt-0.5">High Pressure Steam Trunk</span>
            </div>

            {/* Wellpads Cluster (Center Nodes) */}
            <div className="col-span-6 grid grid-cols-3 gap-2">
              {wells.map((w) => {
                const isCrit = w.diagnosis === "rod_floating";
                return (
                  <Link key={w.well_id} href={`/well/${w.well_id}`} className="group">
                    <div className={`bg-black p-2.5 border transition-colors group-hover:border-zinc-500 ${
                      isCrit ? "border-amber-700 bg-amber-950/10" : "border-zinc-850"
                    }`}>
                      <div className="flex justify-between items-center text-[10px] font-bold">
                        <span className="text-zinc-100">{w.well_id}</span>
                        <span className={`text-[8px] ${PHASE_COLOR[w.phase] ?? "text-zinc-400"}`}>
                          C{w.cycle_number ?? 1}
                        </span>
                      </div>
                      <div className="mt-1 text-[9px] text-zinc-400 flex flex-col gap-0.5">
                        <span>{w.temperature ? `${w.temperature.toFixed(0)}°C` : "—"} • {w.viscosity ? `${Math.round(w.viscosity)} cP` : "—"}</span>
                        <span>WC: <strong className="text-zinc-300">{w.water_cut_pct ?? 35}%</strong></span>
                      </div>
                    </div>
                  </Link>
                );
              })}
            </div>

            {/* GGS Gathering Station (Right Node) */}
            <div className="col-span-3 bg-black p-3 border border-zinc-850 flex flex-col gap-1">
              <div className="flex items-center gap-1.5 text-green-400 text-[10px] font-bold">
                <Layers className="w-3.5 h-3.5" /> GGS Baghewala
              </div>
              <span className="text-[9px] text-zinc-500">Heated Emulsion Treater</span>
              <div className="w-full bg-green-950 h-1 mt-1"><div className="w-[85%] bg-green-400 h-full"></div></div>
              <span className="text-[8px] text-green-400 uppercase mt-0.5">Heavy Bitumen Delivery: 195 BPD</span>
            </div>
          </div>
        </div>

        {/* Live Well Operations Table */}
        <div className="border border-zinc-800 bg-zinc-950">
          <div className="p-3 border-b border-zinc-850 flex justify-between items-center">
            <h2 className="text-[10px] text-zinc-400 uppercase tracking-widest font-bold">
              Subsurface Well Asset Roster &amp; Thermal Degradation Status
            </h2>
            <span className="text-[8px] text-zinc-600 uppercase">Auto-Refresh 1000ms</span>
          </div>

          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-zinc-850 bg-black text-[9px] text-zinc-500 uppercase tracking-widest">
                <th className="px-3.5 py-2.5 font-normal">Asset ID</th>
                <th className="px-3.5 py-2.5 font-normal">CSS Phase</th>
                <th className="px-3.5 py-2.5 font-normal">Cycle #</th>
                <th className="px-3.5 py-2.5 font-normal">BHT (°C)</th>
                <th className="px-3.5 py-2.5 font-normal">Viscosity</th>
                <th className="px-3.5 py-2.5 font-normal">Water Cut</th>
                <th className="px-3.5 py-2.5 font-normal">SOR (t/bbl)</th>
                <th className="px-3.5 py-2.5 font-normal">Daily Margin</th>
                <th className="px-3.5 py-2.5 font-normal">Diagnosis</th>
                <th className="px-3.5 py-2.5 font-normal text-right">SCADA</th>
              </tr>
            </thead>
            <tbody>
              {wells.map((well) => {
                const diag = DIAGNOSIS_SEVERITY[well.diagnosis] ?? DIAGNOSIS_SEVERITY.normal;
                return (
                  <tr key={well.well_id} className="border-b border-zinc-900/60 hover:bg-zinc-900/30 transition-colors">
                    <td className="px-3.5 py-3 font-bold text-zinc-100">{well.well_id}</td>
                    <td className={`px-3.5 py-3 font-semibold ${PHASE_COLOR[well.phase] ?? "text-zinc-400"}`}>
                      {well.phase}
                    </td>
                    <td className="px-3.5 py-3 text-zinc-300 font-bold">
                      Cycle {well.cycle_number ?? 1}
                    </td>
                    <td className="px-3.5 py-3 text-zinc-200">
                      {well.temperature ? `${well.temperature.toFixed(1)}°C` : "—"}
                    </td>
                    <td className="px-3.5 py-3 text-zinc-400">
                      {well.viscosity ? `${Math.round(well.viscosity).toLocaleString()} cP` : "—"}
                    </td>
                    <td className="px-3.5 py-3 text-cyan-400 font-mono">
                      {well.water_cut_pct != null ? `${well.water_cut_pct.toFixed(0)}%` : "—"}
                    </td>
                    <td className="px-3.5 py-3 text-zinc-300 font-mono">
                      {well.sor ? `${well.sor.toFixed(2)}` : (well.phase === "Production" ? "2.40" : "0.00")}
                    </td>
                    <td className="px-3.5 py-3 font-semibold">
                      {well.daily_margin !== undefined ? (
                        <span className={well.daily_margin >= 0 ? "text-green-400" : "text-red-400"}>
                          ${Math.round(well.daily_margin).toLocaleString()}/d
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-3.5 py-3">
                      <span className={`text-[8px] px-2 py-0.5 border uppercase tracking-wider ${diag.style}`}>
                        {diag.label}
                      </span>
                    </td>
                    <td className="px-3.5 py-3 text-right">
                      <Link
                        href={`/well/${well.well_id}`}
                        className="text-zinc-300 hover:text-white transition-colors text-[9px] uppercase tracking-widest border border-zinc-750 hover:border-zinc-500 px-2 py-0.5 bg-zinc-900"
                      >
                        Deep Dive →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
