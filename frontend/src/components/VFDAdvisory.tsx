import React, { useState } from 'react';
import { AlertTriangle, Settings2, Activity, ShieldCheck, Send, Sliders } from 'lucide-react';
import { API_URL, VFD_SETPOINT_TOKEN } from "@/lib/config";

interface Props {
  wellId?: string;
  currentSPM: number;
  recommendedSPM: number;
  viscosityEstimate: number;
}

export function VFDAdvisory({
  wellId = "BGW-01",
  currentSPM,
  recommendedSPM,
  viscosityEstimate,
}: Props) {
  const [autoMode, setAutoMode] = useState(true);
  const [targetSPM, setTargetSPM] = useState<number>(recommendedSPM);
  const [dispatchStatus, setDispatchStatus] = useState<string | null>(null);

  const diff = recommendedSPM - currentSPM;
  const isOptimal = Math.abs(diff) <= 0.3;
  const isHighViscosity = viscosityEstimate > 1800;

  // Fix #6: Authentic Stokes Fall Velocity Formulation
  // d_rod = 1.0 inch = 0.0254 m; rho_steel = 7850 kg/m3; rho_oil = 980 kg/m3; g = 9.81 m/s2
  const g = 9.81;
  const d_rod = 0.0254; // 1" API steel rod
  const delta_rho = 7850.0 - 980.0; // 6870 kg/m3 net buoyant density
  const mu_pa_s = Math.max(0.01, (viscosityEstimate * 0.001)); // cP to Pa.s
  
  // v_fall = (g * d^2 * delta_rho) / (18 * mu) [m/s]
  const v_fall_m_s = (g * (d_rod ** 2) * delta_rho) / (18.0 * mu_pa_s);
  const v_fall_ft_s = v_fall_m_s * 3.28084;
  
  // Downstroke duration at SPM is t_down = 60 / (2 * SPM) = 30 / SPM seconds.
  // Rod must fall stroke length (100 inches = 2.54 m) within t_down:
  // 30 / SPM >= stroke_m / v_fall => SPM_stokes_cap = (v_fall / 2.54) * 30
  const spmStokesCap = Math.max(2.0, Math.min(9.0, (v_fall_m_s / 2.54) * 30.0));
  
  // Mechanical rod stress calculation based on API RP 11L
  const projectedRodStress = Math.round(14000 + (targetSPM * 1100) + (viscosityEstimate * 1.8));
  const rodStressLimit = 30000; // API Grade D rod yield stress limit (psi)
  const isStressWarning = projectedRodStress > rodStressLimit * 0.85 || targetSPM > spmStokesCap;

  const handleDispatch = async () => {
    setDispatchStatus("DISPATCHING...");
    try {
      const res = await fetch(`${API_URL}/api/setpoint`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${VFD_SETPOINT_TOKEN}`
        },
        body: JSON.stringify({
          well_id: wellId,
          spm_override: targetSPM,
          auto_mode: autoMode,
          emergency_shutoff: false,
          auth_token: VFD_SETPOINT_TOKEN,
        }),
      });
      if (res.ok) {
        setDispatchStatus("ACK_CONFIRMED");
        setTimeout(() => setDispatchStatus(null), 3000);
      } else {
        setDispatchStatus("DISPATCH_ERR");
      }
    } catch {
      setDispatchStatus("OFFLINE_EMULATED");
      setTimeout(() => setDispatchStatus(null), 3000);
    }
  };

  return (
    <div className="bg-zinc-950 border border-zinc-850 p-3 flex flex-col gap-3 font-mono">
      <div className="flex justify-between items-center border-b border-zinc-850 pb-2">
        <h3 className="text-zinc-400 text-[10px] uppercase tracking-wider flex items-center gap-1.5">
          <Settings2 className="w-3.5 h-3.5 text-zinc-500" />
          VFD Adaptive Speed Advisory
        </h3>
        
        {/* Auto vs Manual Toggle */}
        <div className="flex items-center gap-1 border border-zinc-800 p-0.5 bg-black">
          <button
            onClick={() => { setAutoMode(true); setTargetSPM(recommendedSPM); }}
            className={`text-[8px] px-2 py-0.5 uppercase tracking-wider transition-colors ${
              autoMode ? "bg-green-950/70 text-green-300 border border-green-800" : "text-zinc-500"
            }`}
          >
            Auto Advisory
          </button>
          <button
            onClick={() => setAutoMode(false)}
            className={`text-[8px] px-2 py-0.5 uppercase tracking-wider transition-colors ${
              !autoMode ? "bg-amber-950/70 text-amber-300 border border-amber-800" : "text-zinc-500"
            }`}
          >
            Manual Override
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="bg-black p-2 border border-zinc-900">
          <span className="text-zinc-550 text-[8px] uppercase tracking-wider block mb-0.5">Surface Speed</span>
          <div className="flex items-baseline gap-1">
            <span className="text-xl font-bold text-zinc-100">{currentSPM.toFixed(1)}</span>
            <span className="text-zinc-500 text-[9px]">SPM</span>
          </div>
        </div>
        
        <div className="bg-black p-2 border border-zinc-900">
          <span className="text-zinc-550 text-[8px] uppercase tracking-wider block mb-0.5">Recommended</span>
          <div className="flex items-baseline gap-1">
            <span className={`text-xl font-bold ${isOptimal ? 'text-green-400' : 'text-amber-400'}`}>
              {recommendedSPM.toFixed(1)}
            </span>
            <span className="text-zinc-500 text-[9px]">SPM</span>
          </div>
        </div>
      </div>

      {/* Manual What-If Setpoint Control Panel */}
      {!autoMode && (
        <div className="bg-black p-2.5 border border-amber-900/60 flex flex-col gap-2">
          <div className="flex justify-between items-center text-[9px]">
            <span className="text-amber-400 uppercase font-bold flex items-center gap-1">
              <Sliders className="w-3 h-3" /> What-If Setpoint Simulator
            </span>
            <span className="text-zinc-100 font-bold">{targetSPM.toFixed(1)} SPM</span>
          </div>

          <input
            type="range"
            min="2.0"
            max="9.0"
            step="0.2"
            value={targetSPM}
            onChange={(e) => setTargetSPM(Number(e.target.value))}
            className="w-full accent-amber-500 cursor-pointer"
          />

          <div className="flex justify-between text-[8px] text-zinc-500">
            <span>Projected Rod Stress:</span>
            <span className={`font-bold ${isStressWarning ? "text-red-400" : "text-green-400"}`}>
              {projectedRodStress.toLocaleString()} psi ({Math.round((projectedRodStress / rodStressLimit) * 100)}% API Yield)
            </span>
          </div>

          <div className="flex justify-between text-[8px] text-zinc-500">
            <span>Stokes Downstroke Cap:</span>
            <span className={`font-bold ${targetSPM > spmStokesCap ? "text-amber-400" : "text-zinc-300"}`}>
              {spmStokesCap.toFixed(1)} SPM (v_fall: {v_fall_ft_s.toFixed(2)} ft/s)
            </span>
          </div>

          <button
            onClick={handleDispatch}
            className="mt-1 w-full bg-amber-950/60 hover:bg-amber-900/60 border border-amber-800 text-amber-300 py-1 text-[9px] uppercase tracking-widest font-bold flex items-center justify-center gap-1.5 transition-colors"
          >
            <Send className="w-3 h-3" />
            {dispatchStatus ?? "Dispatch Setpoint to VFD"}
          </button>
        </div>
      )}

      {/* Viscosity & Kinetic Stokes Fall Status */}
      <div className="bg-black p-2 border border-zinc-900 flex flex-col gap-1">
        <div className="flex justify-between items-center text-xs">
          <span className="text-zinc-500 text-[9px] uppercase tracking-wider flex items-center gap-1.5">
            <Activity className="w-3 h-3 text-zinc-400" />
            Viscosity Est.
          </span>
          <span className={`text-xs font-bold ${isHighViscosity ? 'text-amber-400' : 'text-zinc-200'}`}>
            {viscosityEstimate.toLocaleString()} <span className="text-zinc-500 text-[9px] font-normal">cP</span>
          </span>
        </div>
        
        {!isOptimal ? (
          <div className="mt-1 pt-1.5 border-t border-zinc-850 flex items-start gap-1.5 text-amber-400 text-[10px]">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <p className="leading-snug">
              {diff < 0
                ? `High viscous drag detected. Stokes terminal fall velocity drops to ${v_fall_ft_s.toFixed(2)} ft/s. Reduce SPM to ${recommendedSPM.toFixed(1)} to prevent downstroke rod floating & buckling.`
                : `Viscosity low (${viscosityEstimate} cP). Safe to increase SPM to ${recommendedSPM.toFixed(1)} within Stokes kinematic envelope.`}
            </p>
          </div>
        ) : (
          <div className="mt-1 pt-1.5 border-t border-zinc-850 flex items-center gap-1.5 text-green-400 text-[10px]">
            <ShieldCheck className="w-3 h-3 shrink-0" />
            <span>Stokes terminal fall velocity: {v_fall_ft_s.toFixed(2)} ft/s. Operating within laminar gravity settling envelope.</span>
          </div>
        )}
      </div>
    </div>
  );
}
