"use client";

import React, { useState } from "react";

interface Point {
  pos: number;
  load: number;
}

interface DynacardProps {
  surfaceUp: Point[];
  surfaceDn: Point[];
  downholeUp?: Point[];
  downholeDn?: Point[];
  peakLoad: number;
  minLoad: number;
  cardAreaJoules?: number;
  plungerStrokeIn?: number;
  diagnosis: string;
  confidence: number;
}

const DIAGNOSIS_COLOR: Record<string, { stroke: string; fill: string; border: string }> = {
  normal: { stroke: "#22c55e", fill: "rgba(34, 197, 94, 0.12)", border: "border-green-600" },
  rod_floating: { stroke: "#f59e0b", fill: "rgba(245, 158, 11, 0.12)", border: "border-amber-600" },
  fluid_pound: { stroke: "#ef4444", fill: "rgba(239, 68, 68, 0.12)", border: "border-red-600" },
  gas_interference: { stroke: "#a855f7", fill: "rgba(168, 85, 247, 0.12)", border: "border-purple-600" },
  traveling_valve_leak: { stroke: "#ec4899", fill: "rgba(236, 72, 153, 0.12)", border: "border-pink-600" },
  uncertain: { stroke: "#71717a", fill: "rgba(113, 113, 122, 0.12)", border: "border-zinc-600" },
};

export function DynacardChart({
  surfaceUp = [],
  surfaceDn = [],
  downholeUp = [],
  downholeDn = [],
  peakLoad = 16000,
  minLoad = 4500,
  cardAreaJoules = 1420,
  plungerStrokeIn = 88.5,
  diagnosis = "normal",
  confidence = 0.98,
}: DynacardProps) {
  const [showDownhole, setShowDownhole] = useState(true);
  const theme = DIAGNOSIS_COLOR[diagnosis] ?? DIAGNOSIS_COLOR.normal;

  // ViewBox dimensions
  const vbW = 600;
  const vbH = 340;
  const padL = 60;
  const padR = 25;
  const padT = 25;
  const padB = 40;

  const plotW = vbW - padL - padR;
  const plotH = vbH - padT - padB;

  // Scaling domains: Position [0, 110] in, Load [0, max(peakLoad * 1.15, 20000)] lbs
  const maxPos = 110.0;
  const maxLoad = Math.max(peakLoad * 1.18, 18000.0);

  const scaleX = (pos: number) => padL + (Math.max(0, Math.min(pos, maxPos)) / maxPos) * plotW;
  const scaleY = (load: number) => padT + plotH - (Math.max(0, Math.min(load, maxLoad)) / maxLoad) * plotH;

  // Construct closed SVG path for surface card: Upstroke 0->100 then Downstroke 100->0 then Z
  const buildSvgPath = (up: Point[], dn: Point[]) => {
    if (!up.length || !dn.length) return "";
    let d = "";
    up.forEach((pt, i) => {
      const x = scaleX(pt.pos);
      const y = scaleY(pt.load);
      d += i === 0 ? `M ${x.toFixed(1)} ${y.toFixed(1)}` : ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    });
    dn.forEach((pt) => {
      const x = scaleX(pt.pos);
      const y = scaleY(pt.load);
      d += ` L ${x.toFixed(1)} ${y.toFixed(1)}`;
    });
    d += " Z";
    return d;
  };

  const surfacePath = buildSvgPath(surfaceUp, surfaceDn);
  const downholePath = buildSvgPath(downholeUp, downholeDn);

  // Y-axis ticks
  const yTicks = [0, 5000, 10000, 15000, 20000].filter((v) => v <= maxLoad);
  const xTicks = [0, 25, 50, 75, 100];

  return (
    <div className="flex flex-col h-full bg-black font-mono select-none">
      {/* Top SCADA Control Header */}
      <div className="flex justify-between items-center mb-2 px-1 shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-zinc-500 uppercase tracking-widest">
            Kinematic Card Transform (Hooke + Valve Transfer / Gibbs-Lite)
          </span>
          <span className="text-[9px] text-zinc-600">• SCADA Replay 1Hz (21d in 3min)</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowDownhole(!showDownhole)}
            className={`text-[9px] px-2 py-0.5 border uppercase tracking-wider transition-colors ${
              showDownhole
                ? "border-cyan-600 bg-cyan-950/40 text-cyan-300"
                : "border-zinc-800 text-zinc-500 hover:border-zinc-700"
            }`}
          >
            {showDownhole ? "Hide Downhole Card" : "Show Downhole Card"}
          </button>
          <div
            className={`flex items-center gap-1.5 px-2 py-0.5 border text-[10px] uppercase font-bold tracking-widest ${theme.border}`}
            style={{ color: theme.stroke }}
          >
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: theme.stroke }} />
            {diagnosis.replace("_", " ")}
            <span className="text-[9px] text-zinc-400 font-normal">
              {(confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* SVG Industrial Canvas */}
      <div className="flex-1 w-full min-h-0 relative border border-zinc-850 bg-zinc-950">
        <svg
          viewBox={`0 0 ${vbW} ${vbH}`}
          className="w-full h-full block"
          preserveAspectRatio="none"
        >
          <defs>
            <pattern id="minorGrid" width="15" height="15" patternUnits="userSpaceOnUse">
              <path d="M 15 0 L 0 0 0 15" fill="none" stroke="#18181b" strokeWidth="0.5" />
            </pattern>
          </defs>

          {/* Grid Background */}
          <rect x={padL} y={padT} width={plotW} height={plotH} fill="url(#minorGrid)" />

          {/* Major Grid Lines & Ticks */}
          {yTicks.map((val) => {
            const y = scaleY(val);
            return (
              <g key={`y-${val}`}>
                <line x1={padL} y1={y} x2={padL + plotW} y2={y} stroke="#27272a" strokeWidth="1" strokeDasharray="3 3" />
                <text x={padL - 8} y={y + 3} textAnchor="end" fill="#71717a" fontSize="9" fontFamily="monospace">
                  {(val / 1000).toFixed(0)}k
                </text>
              </g>
            );
          })}

          {xTicks.map((val) => {
            const x = scaleX(val);
            return (
              <g key={`x-${val}`}>
                <line x1={x} y1={padT} x2={x} y2={padT + plotH} stroke="#27272a" strokeWidth="1" strokeDasharray="3 3" />
                <text x={x} y={padT + plotH + 16} textAnchor="middle" fill="#71717a" fontSize="9" fontFamily="monospace">
                  {val}&quot;
                </text>
              </g>
            );
          })}

          {/* Axis Labels */}
          <text
            x={padL + plotW / 2}
            y={vbH - 8}
            textAnchor="middle"
            fill="#52525b"
            fontSize="9"
            letterSpacing="1px"
            fontFamily="monospace"
          >
            POLISHED ROD DISPLACEMENT (INCHES)
          </text>
          <text
            x={16}
            y={padT + plotH / 2}
            textAnchor="middle"
            fill="#52525b"
            fontSize="9"
            letterSpacing="1px"
            transform={`rotate(-90 16 ${padT + plotH / 2})`}
            fontFamily="monospace"
          >
            ROD LOAD (LBS)
          </text>

          {/* Downhole Pump Card (Gibbs Wave) */}
          {showDownhole && downholePath && (
            <g id="downhole-card">
              <path
                d={downholePath}
                fill="rgba(6, 182, 212, 0.10)"
                stroke="#06b6d4"
                strokeWidth="1.5"
                strokeDasharray="4 2"
              />
            </g>
          )}

          {/* Surface Polished Rod Card */}
          {surfacePath && (
            <g id="surface-card">
              <path
                d={surfacePath}
                fill={theme.fill}
                stroke={theme.stroke}
                strokeWidth="1.8"
              />
            </g>
          )}

          {/* Reference Lines for Peak / Min Loads */}
          <line
            x1={padL}
            y1={scaleY(peakLoad)}
            x2={padL + plotW}
            y2={scaleY(peakLoad)}
            stroke="#ef4444"
            strokeWidth="0.8"
            strokeDasharray="2 2"
            opacity="0.6"
          />
        </svg>

        {/* Legend Overlay */}
        <div className="absolute top-3 right-3 bg-black/80 border border-zinc-800 p-2 flex flex-col gap-1 text-[9px] pointer-events-none">
          <div className="flex items-center gap-2">
            <span className="w-3 h-0.5" style={{ backgroundColor: theme.stroke }} />
            <span className="text-zinc-300">Surface Card (PRL)</span>
          </div>
          {showDownhole && (
            <div className="flex items-center gap-2">
              <span className="w-3 h-0.5 border-t border-dashed border-cyan-400" />
              <span className="text-cyan-400">Downhole Pump Card</span>
            </div>
          )}
        </div>
      </div>

      {/* Industrial Engineering Metrics Bar */}
      <div className="grid grid-cols-4 gap-2 mt-2 pt-2 border-t border-zinc-850 shrink-0 text-xs font-mono">
        <div>
          <span className="text-zinc-600 block text-[8px] uppercase tracking-wider">Surface Peak Load</span>
          <span className="text-zinc-200 font-bold">{peakLoad.toLocaleString()} <span className="text-zinc-500 font-normal">lbs</span></span>
        </div>
        <div>
          <span className="text-zinc-600 block text-[8px] uppercase tracking-wider">Min Rod Load</span>
          <span className="text-zinc-200 font-bold">{minLoad.toLocaleString()} <span className="text-zinc-500 font-normal">lbs</span></span>
        </div>
        <div>
          <span className="text-zinc-600 block text-[8px] uppercase tracking-wider">Plunger Stroke</span>
          <span className="text-cyan-400 font-bold">{plungerStrokeIn} <span className="text-zinc-500 font-normal">in</span></span>
        </div>
        <div>
          <span className="text-zinc-600 block text-[8px] uppercase tracking-wider">Pump Work / Stroke</span>
          <span className="text-zinc-200 font-bold">{cardAreaJoules.toLocaleString()} <span className="text-zinc-500 font-normal">J</span></span>
        </div>
      </div>
    </div>
  );
}
