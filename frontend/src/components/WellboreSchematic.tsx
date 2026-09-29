"use client";

import React, { useState } from "react";

interface DepthPoint {
  depth_m: number;
  temp_c: number;
  visc_cp: number;
}

interface Props {
  depthPoints?: DepthPoint[];
  pumpDepthM?: number;
  phase?: string;
}

export function WellboreSchematic({
  depthPoints = [],
  pumpDepthM = 1000,
  phase = "Production",
}: Props) {
  const [activeTab, setActiveTab] = useState<"temp" | "visc">("temp");

  // Fallback points if none provided
  const points = depthPoints.length > 0 ? depthPoints : [
    { depth_m: 0, temp_c: 48.0, visc_cp: 6500.0 },
    { depth_m: 250, temp_c: 56.0, visc_cp: 4200.0 },
    { depth_m: 500, temp_c: 68.0, visc_cp: 2400.0 },
    { depth_m: 750, temp_c: 84.0, visc_cp: 1100.0 },
    { depth_m: 1000, temp_c: 102.0, visc_cp: 520.0 },
    { depth_m: 1200, temp_c: 125.0, visc_cp: 240.0 },
  ];

  const maxDepth = 1250;
  const vbW = 280;
  const vbH = 340;
  const padT = 20;
  const padB = 25;
  const plotH = vbH - padT - padB;

  const scaleY = (depth: number) => padT + (depth / maxDepth) * plotH;

  // Wellbore centerline & width
  const cx = 70;
  const csgW = 32;
  const tubW = 18;
  const rodW = 4;

  // Temperature / Viscosity curve scale
  const curveL = 135;
  const curveW = 125;

  const minTemp = 20;
  const maxTemp = 320;
  const scaleTempX = (t: number) => curveL + ((t - minTemp) / (maxTemp - minTemp)) * curveW;

  const minViscLog = 1; // log10(10 cP) = 1
  const maxViscLog = 4.7; // log10(50000 cP) = 4.7
  const scaleViscX = (v: number) => {
    const logV = Math.log10(Math.max(v, 10));
    return curveL + ((logV - minViscLog) / (maxViscLog - minViscLog)) * curveW;
  };

  // Build SVG path for gradient curve
  let curvePath = "";
  points.forEach((pt, i) => {
    const y = scaleY(pt.depth_m);
    const x = activeTab === "temp" ? scaleTempX(pt.temp_c) : scaleViscX(pt.visc_cp);
    curvePath += i === 0 ? `M ${x.toFixed(1)} ${y.toFixed(1)}` : ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
  });

  return (
    <div className="flex flex-col h-full bg-black font-mono select-none">
      {/* Header with selector */}
      <div className="flex justify-between items-center mb-2 px-1 shrink-0">
        <span className="text-[10px] text-zinc-500 uppercase tracking-widest">
          Subsurface Wellbore Profile
        </span>
        <div className="flex items-center gap-1 border border-zinc-800 p-0.5 bg-zinc-950">
          <button
            onClick={() => setActiveTab("temp")}
            className={`text-[8px] px-2 py-0.5 uppercase tracking-wider transition-colors ${
              activeTab === "temp" ? "bg-amber-950/60 text-amber-300 border border-amber-800" : "text-zinc-500"
            }`}
          >
            Temp T(z)
          </button>
          <button
            onClick={() => setActiveTab("visc")}
            className={`text-[8px] px-2 py-0.5 uppercase tracking-wider transition-colors ${
              activeTab === "visc" ? "bg-cyan-950/60 text-cyan-300 border border-cyan-800" : "text-zinc-500"
            }`}
          >
            Visc μ(z)
          </button>
        </div>
      </div>

      {/* SVG Completion Schematic & Gradient Curve */}
      <div className="flex-1 w-full min-h-0 relative border border-zinc-850 bg-zinc-950">
        <svg viewBox={`0 0 ${vbW} ${vbH}`} className="w-full h-full block" preserveAspectRatio="none">
          {/* Depth Reference Grid */}
          {[0, 250, 500, 750, 1000, 1200].map((d) => {
            const y = scaleY(d);
            return (
              <g key={`d-${d}`}>
                <line x1={20} y1={y} x2={vbW - 10} y2={y} stroke="#18181b" strokeWidth="0.8" strokeDasharray="2 2" />
                <text x={18} y={y + 3} textAnchor="end" fill="#52525b" fontSize="8" fontFamily="monospace">
                  {d}m
                </text>
              </g>
            );
          })}

          {/* Surface Casing (0 to 250m) */}
          <rect x={cx - csgW / 2} y={padT} width={csgW} height={scaleY(250) - padT} fill="#27272a" stroke="#3f3f46" strokeWidth="0.8" />
          <polygon points={`${cx - csgW / 2 - 3},${scaleY(250)} ${cx - csgW / 2},${scaleY(250) - 8} ${cx - csgW / 2},${scaleY(250)}`} fill="#71717a" />
          <polygon points={`${cx + csgW / 2 + 3},${scaleY(250)} ${cx + csgW / 2},${scaleY(250) - 8} ${cx + csgW / 2},${scaleY(250)}`} fill="#71717a" />

          {/* Production Tubing (0 to 1000m) */}
          <rect x={cx - tubW / 2} y={padT} width={tubW} height={scaleY(1000) - padT} fill="#09090b" stroke="#52525b" strokeWidth="0.8" />

          {/* Sucker Rod String (0 to 1000m) */}
          <line x1={cx} y1={padT} x2={cx} y2={scaleY(1000)} stroke="#a1a1aa" strokeWidth={rodW} />

          {/* SRP Plunger Pump at 1000m */}
          <rect x={cx - tubW / 2 + 1} y={scaleY(980)} width={tubW - 2} height={20} fill="#f59e0b" stroke="#d97706" strokeWidth="0.8" opacity="0.9" />

          {/* Perforations Zone in Jodhpur Sandstone (1150m to 1200m) */}
          <rect x={cx - csgW / 2} y={scaleY(1150)} width={csgW} height={scaleY(1200) - scaleY(1150)} fill="rgba(245, 158, 11, 0.15)" stroke="#d97706" strokeWidth="0.8" strokeDasharray="2 2" />
          {/* Perforation arrows */}
          {[-1, 1].map((dir, idx) => (
            <g key={`perf-${idx}`}>
              <line x1={cx + dir * (csgW / 2 + 2)} y1={scaleY(1160)} x2={cx + dir * (csgW / 2 + 7)} y2={scaleY(1160)} stroke="#f59e0b" strokeWidth="1" />
              <line x1={cx + dir * (csgW / 2 + 2)} y1={scaleY(1175)} x2={cx + dir * (csgW / 2 + 7)} y2={scaleY(1175)} stroke="#f59e0b" strokeWidth="1" />
              <line x1={cx + dir * (csgW / 2 + 2)} y1={scaleY(1190)} x2={cx + dir * (csgW / 2 + 7)} y2={scaleY(1190)} stroke="#f59e0b" strokeWidth="1" />
            </g>
          ))}

          {/* Curve Plotting Area Header */}
          <line x1={curveL} y1={padT} x2={curveL + curveW} y2={padT} stroke="#27272a" strokeWidth="1" />
          <line x1={curveL} y1={padT + plotH} x2={curveL + curveW} y2={padT + plotH} stroke="#27272a" strokeWidth="1" />

          {/* Dynamic Gradient Curve */}
          {curvePath && (
            <path
              d={curvePath}
              fill="none"
              stroke={activeTab === "temp" ? "#f59e0b" : "#06b6d4"}
              strokeWidth="2"
              strokeLinecap="round"
            />
          )}

          {/* Gradient Data Nodes */}
          {points.map((pt, i) => {
            const y = scaleY(pt.depth_m);
            const x = activeTab === "temp" ? scaleTempX(pt.temp_c) : scaleViscX(pt.visc_cp);
            return (
              <circle
                key={`node-${i}`}
                cx={x}
                cy={y}
                r="2.5"
                fill="#000000"
                stroke={activeTab === "temp" ? "#f59e0b" : "#06b6d4"}
                strokeWidth="1.2"
              />
            );
          })}

          {/* X-axis labels for gradient */}
          <text x={curveL} y={vbH - 8} fill="#71717a" fontSize="7" fontFamily="monospace">
            {activeTab === "temp" ? "20°C" : "10 cP"}
          </text>
          <text x={curveL + curveW} y={vbH - 8} textAnchor="end" fill="#71717a" fontSize="7" fontFamily="monospace">
            {activeTab === "temp" ? "320°C" : "50k cP"}
          </text>
        </svg>

        {/* Legend overlays */}
        <div className="absolute bottom-2 left-2 bg-black/85 border border-zinc-800 p-1.5 text-[8px] text-zinc-400">
          <div>• Pump: <span className="text-amber-400">{pumpDepthM}m</span></div>
          <div>• Perfs: <span className="text-zinc-200">1150-1200m</span></div>
        </div>
      </div>

      {/* Footer Readouts */}
      <div className="grid grid-cols-2 gap-2 mt-2 pt-1.5 border-t border-zinc-850 text-xs font-mono">
        <div>
          <span className="text-zinc-600 block text-[8px] uppercase">Wellhead Temp</span>
          <span className="text-zinc-200 font-bold">{points[0]?.temp_c ?? 48}°C</span>
        </div>
        <div>
          <span className="text-zinc-600 block text-[8px] uppercase">Sandface Temp</span>
          <span className="text-amber-400 font-bold">{points[points.length - 1]?.temp_c ?? 125}°C</span>
        </div>
      </div>
    </div>
  );
}
