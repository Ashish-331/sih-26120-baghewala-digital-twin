"use client";

import { useEffect, useState, useRef } from "react";
import { BannerWatermark, Watermark } from "@/components/Watermark";
import { CyclePhaseIndicator } from "@/components/CyclePhaseIndicator";
import { DynacardChart } from "@/components/DynacardChart";
import { VFDAdvisory } from "@/components/VFDAdvisory";
import { WellboreSchematic } from "@/components/WellboreSchematic";
import { Activity, Layers } from "lucide-react";

interface Point {
  pos: number;
  load: number;
}

interface DynacardPayload {
  surface_up: Point[];
  surface_dn: Point[];
  downhole_up: Point[];
  downhole_dn: Point[];
  plunger_stroke_in: number;
  card_area_joules: number;
  surface_peak_load: number;
  surface_min_load: number;
}

interface EconomicMetrics {
  oil_price_usd_bbl: number;
  steam_cost_usd_ton: number;
  daily_oil_bpd: number;
  daily_steam_tons: number;
  current_sor: number;
  economic_cutoff_sor: number;
  net_daily_margin_usd: number;
  days_to_sor_cutoff: number;
}

interface DepthPoint {
  depth_m: number;
  temp_c: number;
  visc_cp: number;
}

interface WellboreProfile {
  depth_points: DepthPoint[];
  pump_depth_m: number;
  perforations_top_m: number;
  perforations_bottom_m: number;
}

interface TelemetryData {
  timestamp: string;
  well_id: string;
  load: number;
  position: number;
  temperature: number;
  viscosity: number;
  spm: number;
  diagnosis: string;
  confidence: number;
  phase: string;
  cycle_number?: number;
  water_cut_pct?: number;
  phase_day: number;
  tubing_psi: number;
  casing_psi: number;
  dynacard?: DynacardPayload;
  economics?: EconomicMetrics;
  wellbore_profile?: WellboreProfile;
}

interface LogEntry {
  timestamp: string;
  event: string;
  diagnosis: string;
  severity: "info" | "warning" | "critical";
}

export default function WellDeepDive({ params }: { params: { id: string } }) {
  const [telemetry, setTelemetry] = useState<TelemetryData | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const [activeView, setActiveView] = useState<"dynacard" | "wellbore">("dynacard");
  const wsRef = useRef<WebSocket | null>(null);
  const wellId = decodeURIComponent(params.id);

  useEffect(() => {
    function connect() {
      wsRef.current = new WebSocket("ws://127.0.0.1:8000/ws/telemetry");
      wsRef.current.onopen = () => setConnected(true);
      wsRef.current.onclose = () => {
        setConnected(false);
        setTimeout(connect, 1500);
      };
      wsRef.current.onerror = () => wsRef.current?.close();
      wsRef.current.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type === "telemetry" && payload.data.well_id === wellId) {
            const data: TelemetryData = payload.data;
            setTelemetry(data);

            if (data.diagnosis !== "normal") {
              const sev: "info" | "warning" | "critical" = data.diagnosis === "rod_floating" ? "warning" : "critical";
              setLogs((prev) => [
                {
                  timestamp: data.timestamp,
                  event: `ML Anomaly: ${data.diagnosis.replace("_", " ").toUpperCase()} detected (${(data.confidence * 100).toFixed(0)}% conf)`,
                  diagnosis: data.diagnosis,
                  severity: sev,
                },
                ...prev,
              ].slice(0, 25));
            }
            if (payload.alert) {
              const alertSev: "info" | "warning" | "critical" = "warning";
              setLogs((prev) => [
                {
                  timestamp: payload.alert.timestamp,
                  event: `Advisory: ${payload.alert.recommendation} | SOR ${payload.alert.sor}`,
                  diagnosis: "advisory",
                  severity: alertSev,
                },
                ...prev,
              ].slice(0, 25));
            }
          }
        } catch (e) {
          console.error("WS Parse error", e);
        }
      };
    }
    connect();
    return () => wsRef.current?.close();
  }, [wellId]);

  const card = telemetry?.dynacard;
  const econ = telemetry?.economics;
  const wellbore = telemetry?.wellbore_profile;

  return (
    <main className="flex flex-col h-screen relative overflow-hidden font-mono bg-black text-zinc-300">
      <Watermark />
      <BannerWatermark />

      {/* Industrial Header */}
      <header className="h-10 border-b border-zinc-800 bg-black px-4 flex justify-between items-center shrink-0">
        <div className="flex items-center gap-3">
          <span className={`w-2 h-2 rounded-none ${connected ? "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.8)]" : "bg-red-600 animate-pulse"}`} />
          <h1 className="text-xs tracking-widest font-bold text-zinc-100 uppercase">
            SCADA WELL UNIT // {wellId}
          </h1>
          <span className="text-[9px] text-zinc-500 uppercase px-1.5 py-0.5 bg-zinc-900 border border-zinc-800">
            Jodhpur Formation • Cycle {telemetry?.cycle_number ?? 1}
          </span>
        </div>
        <div className="flex gap-5 text-[9px] tracking-widest uppercase text-zinc-400">
          <span>Phase: <strong className="text-zinc-200">{telemetry?.phase ?? "AWAITING"}</strong></span>
          <span>BHT: <strong className="text-zinc-200">{telemetry?.temperature?.toFixed(1) ?? "—"}°C</strong></span>
          <span>Visc: <strong className="text-amber-400">{telemetry?.viscosity?.toFixed(0) ?? "—"} cP</strong></span>
          <span>Water Cut: <strong className="text-cyan-400">{telemetry?.water_cut_pct?.toFixed(0) ?? "—"}%</strong></span>
          <span>SPM: <strong className="text-green-400">{telemetry?.spm?.toFixed(1) ?? "—"}</strong></span>
        </div>
      </header>

      {/* Edge-to-Edge Industrial Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-[1px] bg-zinc-800 overflow-hidden">
        
        {/* Left Column: CSS Cycle + Interactive VFD + Economics */}
        <div className="lg:col-span-4 bg-zinc-800 flex flex-col gap-[1px] overflow-y-auto">
          
          {/* Phase Tracking */}
          <div className="bg-black p-3 shrink-0">
            <CyclePhaseIndicator
              currentPhase={(telemetry?.phase as any) ?? "Production"}
              daysInPhase={Math.max(0, Math.round(telemetry?.phase_day ?? (telemetry?.phase === "Injection" ? 4 : telemetry?.phase === "Soak" ? 2 : 8)))}
              totalCycleDays={21}
            />
          </div>

          {/* VFD Open-Loop Advisory with Closed-Loop Setpoint Dispatch */}
          <div className="bg-black p-3 shrink-0">
            <VFDAdvisory
              wellId={wellId}
              currentSPM={telemetry?.spm ?? 6.5}
              recommendedSPM={
                telemetry?.viscosity && telemetry.viscosity > 2200 ? 3.8 :
                (telemetry?.viscosity && telemetry.viscosity > 700 ? 5.0 : 6.5)
              }
              viscosityEstimate={telemetry?.viscosity ?? 800}
            />
          </div>

          {/* Real-time Economic Margin & SOR Cutoff Tracker */}
          <div className="bg-black p-3 flex-1 flex flex-col justify-between">
            <div>
              <div className="flex justify-between items-center border-b border-zinc-850 pb-1.5 mb-2.5">
                <span className="text-[9px] text-zinc-500 uppercase tracking-widest">
                  Well Economics (PPAC Indian Basket)
                </span>
                <span className="text-[8px] text-zinc-650 uppercase">Open-Loop ROI</span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-zinc-950 p-2 border border-zinc-850">
                  <span className="text-zinc-600 block text-[8px] uppercase">Daily Net Margin</span>
                  <span className={`text-sm font-bold ${econ && econ.net_daily_margin_usd >= 0 ? "text-green-400" : "text-red-400"}`}>
                    ${econ?.net_daily_margin_usd ? econ.net_daily_margin_usd.toLocaleString() : "---"}
                    <span className="text-[9px] text-zinc-500 font-normal">/day</span>
                  </span>
                </div>

                <div className="bg-zinc-950 p-2 border border-zinc-850">
                  <span className="text-zinc-600 block text-[8px] uppercase">Current SOR</span>
                  <span className="text-sm font-bold text-zinc-200">
                    {econ?.current_sor?.toFixed(2) ?? "---"}
                    <span className="text-[9px] text-zinc-500 font-normal"> t/bbl</span>
                  </span>
                </div>

                <div className="bg-zinc-950 p-2 border border-zinc-850">
                  <span className="text-zinc-600 block text-[8px] uppercase">Breakeven Cutoff</span>
                  <span className="text-xs text-amber-400">
                    {econ?.economic_cutoff_sor?.toFixed(2) ?? "3.16"} t/bbl
                  </span>
                </div>

                <div className="bg-zinc-950 p-2 border border-zinc-850">
                  <span className="text-zinc-600 block text-[8px] uppercase">Est. Days to Steaming</span>
                  <span className="text-xs text-cyan-400 font-bold">
                    {econ?.days_to_sor_cutoff !== undefined ? `${econ.days_to_sor_cutoff} days` : "---"}
                  </span>
                </div>
              </div>
            </div>

            {/* Live Subsurface Telemetry Registers */}
            <div className="mt-3 pt-2 border-t border-zinc-850">
              <span className="text-[8px] text-zinc-600 uppercase tracking-widest block mb-1">
                Sandface Physical Registers
              </span>
              <div className="grid grid-cols-4 gap-1 text-[10px]">
                <div className="bg-zinc-950 p-1 border border-zinc-900">
                  <span className="text-zinc-650 block text-[7px]">OIL (BPD)</span>
                  <span className="text-zinc-200">{econ?.daily_oil_bpd?.toFixed(0) ?? "—"}</span>
                </div>
                <div className="bg-zinc-950 p-1 border border-zinc-900">
                  <span className="text-zinc-650 block text-[7px]">STEAM (T/D)</span>
                  <span className="text-zinc-200">{econ?.daily_steam_tons?.toFixed(0) ?? "—"}</span>
                </div>
                <div className="bg-zinc-950 p-1 border border-zinc-900">
                  <span className="text-zinc-650 block text-[7px]">P_TUB (psi)</span>
                  <span className="text-zinc-200">{telemetry?.tubing_psi?.toFixed(0) ?? "142"}</span>
                </div>
                <div className="bg-zinc-950 p-1 border border-zinc-900">
                  <span className="text-zinc-650 block text-[7px]">P_CAS (psi)</span>
                  <span className="text-zinc-200">{telemetry?.casing_psi?.toFixed(0) ?? "86"}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Tabbed View (Gibbs Dynacard vs Subsurface Wellbore Gradient) */}
        <div className="lg:col-span-8 bg-zinc-800 flex flex-col gap-[1px]">
          
          {/* View Tab Selector */}
          <div className="bg-black px-4 py-1.5 border-b border-zinc-850 flex justify-between items-center shrink-0">
            <div className="flex gap-2">
              <button
                onClick={() => setActiveView("dynacard")}
                className={`text-[9px] uppercase tracking-wider px-2.5 py-1 border transition-colors flex items-center gap-1.5 ${
                  activeView === "dynacard"
                    ? "bg-zinc-900 border-zinc-600 text-zinc-100 font-bold"
                    : "border-zinc-850 text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <Activity className="w-3 h-3" />
                Gibbs 1D Dynacard Analysis
              </button>
              <button
                onClick={() => setActiveView("wellbore")}
                className={`text-[9px] uppercase tracking-wider px-2.5 py-1 border transition-colors flex items-center gap-1.5 ${
                  activeView === "wellbore"
                    ? "bg-zinc-900 border-zinc-600 text-zinc-100 font-bold"
                    : "border-zinc-850 text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <Layers className="w-3 h-3" />
                Subsurface Wellbore Gradient T(z)
              </button>
            </div>
            <span className="text-[8px] text-zinc-600 uppercase">
              {activeView === "dynacard" ? "1D Damped Wave Solver" : "Ramey (1962) Heat Loss Model"}
            </span>
          </div>

          {/* Active Visual Canvas */}
          <div className="bg-black p-3 flex-1 min-h-0">
            {activeView === "dynacard" ? (
              <DynacardChart
                surfaceUp={card?.surface_up ?? []}
                surfaceDn={card?.surface_dn ?? []}
                downholeUp={card?.downhole_up ?? []}
                downholeDn={card?.downhole_dn ?? []}
                peakLoad={card?.surface_peak_load ?? telemetry?.load ?? 16000}
                minLoad={card?.surface_min_load ?? 4500}
                cardAreaJoules={card?.card_area_joules ?? 1420}
                plungerStrokeIn={card?.plunger_stroke_in ?? 88.5}
                diagnosis={telemetry?.diagnosis ?? "normal"}
                confidence={telemetry?.confidence ?? 0.95}
              />
            ) : (
              <WellboreSchematic
                depthPoints={wellbore?.depth_points ?? []}
                pumpDepthM={wellbore?.pump_depth_m ?? 1000}
                phase={telemetry?.phase}
              />
            )}
          </div>

          {/* Event Historian */}
          <div className="bg-black p-3 h-32 flex flex-col overflow-hidden shrink-0">
            <div className="flex justify-between items-center border-b border-zinc-850 pb-1 mb-1.5 shrink-0">
              <span className="text-[9px] text-zinc-500 uppercase tracking-widest">
                SCADA Event Historian &amp; ML Audit Trail
              </span>
              <span className="text-[8px] text-zinc-600 font-mono">Real-time Telemetry Ingestion</span>
            </div>
            
            <div className="overflow-y-auto flex-1 text-[10px] leading-tight pr-2">
              <table className="w-full text-left">
                <tbody>
                  {logs.length === 0 && (
                    <tr>
                      <td className="text-zinc-650 py-2 italic text-center">
                        Streaming live telemetry... No anomalous events detected.
                      </td>
                    </tr>
                  )}
                  {logs.map((log, i) => (
                    <tr key={i} className="border-b border-zinc-900/40 hover:bg-zinc-950">
                      <td className="py-1 text-zinc-550 w-20 text-[9px]">
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </td>
                      <td className={`py-1 ${
                        log.severity === "critical" ? "text-red-400 font-bold" :
                        log.severity === "warning" ? "text-amber-400" : "text-zinc-300"
                      }`}>
                        {log.event}
                      </td>
                      <td className="py-1 text-right text-[8px] text-zinc-600 w-16">
                        [SYS_ACK]
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}
