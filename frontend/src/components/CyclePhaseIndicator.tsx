import React from 'react';
import { cn } from '@/lib/utils';

export type CSSPhase = 'Injection' | 'Soak' | 'Production';

interface Props {
  currentPhase: CSSPhase;
  daysInPhase: number;
  totalCycleDays: number;
}

export function CyclePhaseIndicator({ currentPhase, daysInPhase, totalCycleDays }: Props) {
  const phases: CSSPhase[] = ['Injection', 'Soak', 'Production'];

  return (
    <div className="bg-zinc-900 border border-zinc-800 p-4 flex flex-col gap-4">
      <div className="flex justify-between items-end">
        <h3 className="text-zinc-400 font-mono text-xs uppercase tracking-wider">CSS Cycle Status</h3>
        <div className="text-right">
          <span className="text-zinc-100 font-mono text-xl">{daysInPhase}</span>
          <span className="text-zinc-500 font-mono text-xs ml-1">Days</span>
        </div>
      </div>
      
      <div className="flex items-center gap-1 w-full">
        {phases.map((phase, idx) => {
          const isActive = currentPhase === phase;
          const isPast = phases.indexOf(currentPhase) > idx;
          
          return (
            <div key={phase} className="flex-1 flex flex-col gap-2">
              <div 
                className={cn(
                  "h-1.5 w-full",
                  isActive ? "bg-amber-500" : isPast ? "bg-zinc-600" : "bg-zinc-800"
                )}
              />
              <div className="flex justify-between items-center px-1">
                <span className={cn(
                  "font-mono text-[10px] uppercase",
                  isActive ? "text-amber-500 font-bold" : isPast ? "text-zinc-400" : "text-zinc-600"
                )}>
                  {phase}
                </span>
                {isActive && (
                  <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse" />
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="pt-2 mt-2 border-t border-zinc-800 flex justify-between items-center text-xs font-mono text-zinc-500">
        <span>Cycle Duration: {totalCycleDays} days</span>
        <span className="text-zinc-400">Target SOR Transition: 3.5</span>
      </div>
    </div>
  );
}
