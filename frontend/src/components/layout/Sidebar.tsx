import Link from "next/link";

export function Sidebar() {
  return (
    <aside className="w-16 lg:w-48 bg-black border-r border-zinc-800 flex flex-col h-screen font-mono sticky top-0 shrink-0 z-50">
      <div className="h-10 border-b border-zinc-800 flex items-center justify-center lg:justify-start lg:px-4">
        <div className="w-2.5 h-2.5 bg-green-500 rounded-none shadow-[0_0_6px_rgba(34,197,94,0.8)]"></div>
        <span className="hidden lg:block ml-3 text-xs font-bold text-zinc-100 tracking-widest">SYS-TWIN</span>
      </div>
      
      <nav className="flex-1 py-3 flex flex-col gap-1.5">
        <Link href="/" className="px-4 py-2.5 text-zinc-500 hover:text-zinc-100 hover:bg-zinc-900 transition-colors flex items-center group">
          <span className="text-base">⊞</span>
          <span className="hidden lg:block ml-3 text-[9px] uppercase tracking-widest group-hover:text-zinc-100 transition-colors">Field Fleet</span>
        </Link>
        <Link href="/surface" className="px-4 py-2.5 text-zinc-500 hover:text-zinc-100 hover:bg-zinc-900 transition-colors flex items-center group">
          <span className="text-base">♨</span>
          <span className="hidden lg:block ml-3 text-[9px] uppercase tracking-widest group-hover:text-zinc-100 transition-colors">Surface Network</span>
        </Link>
        <Link href="/well/BGW-01" className="px-4 py-2.5 text-zinc-500 hover:text-zinc-100 hover:bg-zinc-900 transition-colors flex items-center group">
          <span className="text-base">⚡</span>
          <span className="hidden lg:block ml-3 text-[9px] uppercase tracking-widest group-hover:text-zinc-100 transition-colors">SCADA Wellbore</span>
        </Link>
        <Link href="/analytics" className="px-4 py-2.5 text-zinc-500 hover:text-zinc-100 hover:bg-zinc-900 transition-colors flex items-center group">
          <span className="text-base">∿</span>
          <span className="hidden lg:block ml-3 text-[9px] uppercase tracking-widest group-hover:text-zinc-100 transition-colors">AI Historian</span>
        </Link>
      </nav>
      
      <div className="p-3 border-t border-zinc-800">
        <div className="flex justify-between text-[8px] text-zinc-600 uppercase mb-1">
          <span>Replay Engine</span>
          <span className="text-green-500 font-bold">1 Hz Replay</span>
        </div>
        <div className="text-[7px] text-zinc-600 uppercase mb-1">
          21 Days CSS → 3 Min Demo
        </div>
        <div className="w-full bg-zinc-900 h-1"><div className="w-[92%] bg-green-500 h-full"></div></div>
      </div>
    </aside>
  );
}
