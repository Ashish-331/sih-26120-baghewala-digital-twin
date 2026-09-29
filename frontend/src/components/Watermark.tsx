import React from 'react';

export function Watermark() {
  return (
    <div className="fixed inset-0 pointer-events-none flex items-center justify-center z-50 overflow-hidden opacity-5">
      <div className="transform -rotate-45 text-9xl font-black text-red-500 whitespace-nowrap tracking-widest uppercase">
        Illustrative - Uncalibrated
      </div>
    </div>
  );
}

export function BannerWatermark() {
  return (
    <div className="w-full bg-red-900/40 text-red-400 text-xs font-mono py-1 px-4 text-center border-b border-red-900/50 uppercase tracking-widest flex items-center justify-center gap-2">
      <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
      Illustrative Data - Uncalibrated to Field - Not for Operational Use
    </div>
  );
}
