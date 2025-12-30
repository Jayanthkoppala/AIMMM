"use client";

import { Button } from "./ui/button";
import { usePrivyWallet } from "@/app/hooks/use-privy-wallet";
import { 
  Terminal,
  ArrowRight,
  Activity,
  Cpu,
  Database,
  Zap,
  Lock,
  TrendingUp,
  Power,
  ShieldCheck,
  Globe,
  Server,
  Play
} from "lucide-react";

// --- Data Config ---

const systemProcesses = [
  {
    pid: "8021",
    icon: Cpu,
    name: "NEURAL_ENGINE",
    cmd: "ai.analyze()",
    status: "RUNNING",
    desc: "Real-time pattern recognition",
    load: "89%"
  },
  {
    pid: "4402",
    icon: Activity,
    name: "DATA_INGEST",
    cmd: "data.stream()",
    status: "ACTIVE",
    desc: "OHLCV 1m interval stream",
    load: "12%"
  },
  {
    pid: "1190",
    icon: Database,
    name: "SENTIMENT_SCAN",
    cmd: "sentiment.scan()",
    status: "LISTENING",
    desc: "Social aggregation parser",
    load: "45%"
  },
  {
    pid: "3321",
    icon: TrendingUp,
    name: "TECH_ANALYSIS",
    cmd: "indicators.calc()",
    status: "COMPUTING",
    desc: "RSI, MACD, BB, Vol Profile",
    load: "67%"
  },
  {
    pid: "0012",
    icon: Zap,
    name: "AUTO_EXEC",
    cmd: "agent.execute()",
    status: "STANDBY",
    desc: "Autonomous trade routing",
    load: "0%"
  },
  {
    pid: "9901",
    icon: Lock,
    name: "SECURE_VAULT",
    cmd: "wallet.secure()",
    status: "LOCKED",
    desc: "MPC encryption active",
    load: "100%"
  },
];

const bootLog = [
  { type: "sys", text: "BIOS CHECK .......................... OK" },
  { type: "sys", text: "LOADING KERNEL ...................... OK" },
  { type: "cmd", text: "> mount /dev/movement-mainnet" },
  { type: "res", text: "MOUNTED: 0x82...3f1a [RW]" },
  { type: "cmd", text: "> init trading_agent_v2" },
  { type: "res", text: "ALLOCATING NEURAL NET ..." },
  { type: "sys", text: "ESTABLISHING SECURE TUNNEL" },
  { type: "success", text: "SYSTEM READY. AWAITING INPUT." },
];

// --- Sub-Components ---

function StatusBadge({ label, active = true }: { label: string, active?: boolean }) {
  return (
    <div className="flex items-center gap-2 px-3 py-1 bg-[#0a0a0a] border border-[#1a1a1a]">
      <div className={`w-1.5 h-1.5 rounded-full ${active ? "bg-[#00ff00] animate-pulse" : "bg-[#ff3333]"}`} />
      <span className="text-[10px] font-mono text-[#006600] uppercase tracking-wider">{label}</span>
    </div>
  );
}

function DiagnosticRow({ label, value }: { label: string, value: string }) {
  return (
    <div className="flex justify-between items-center text-xs font-mono border-b border-[#1a1a1a] py-1 last:border-0">
      <span className="text-[#006600]">{label}</span>
      <span className="text-[#00ff00]">{value}</span>
    </div>
  );
}

// --- Main Layout ---

export function LandingPage() {
  const { login } = usePrivyWallet();

  return (
    <div className="min-h-screen bg-black text-[#00ff00] font-mono selection:bg-[#00ff00] selection:text-black flex flex-col relative overflow-hidden">
      
      {/* Background Decor: Grid */}
      <div className="fixed inset-0 pointer-events-none opacity-10" 
           style={{ backgroundImage: 'linear-gradient(#00ff00 1px, transparent 1px), linear-gradient(90deg, #00ff00 1px, transparent 1px)', backgroundSize: '40px 40px' }} 
      />
      
      {/* Background Decor: Vignette */}
      <div className="fixed inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,transparent_0%,black_100%)]" />

   

      {/* --- MAIN CONTENT AREA --- */}
      <main className="flex-1 container mx-auto px-4 py-8 relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* LEFT COLUMN: HERO & IDENTITY (7 cols) */}
        <div className="lg:col-span-7 flex flex-col justify-center gap-8">
          
          {/* Hero Text */}
          <div className="space-y-6">
            <div className="inline-block border border-[#00ff00] px-2 py-0.5 text-[10px] bg-[#00ff00]/10 mb-2">
              :: SYSTEM INITIALIZED
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold tracking-tighter leading-[0.9] text-transparent bg-clip-text bg-gradient-to-b from-[#00ff00] to-[#004400]">
              AUTONOMOUS<br/>
              TRADING<br/>
              PROTOCOL
            </h1>
            
            <p className="text-[#00aa00] text-lg max-w-lg leading-relaxed border-l-2 border-[#004400] pl-4">
              Deploy intelligent agents to the Movement Network. 
              Real-time sentiment parsing meets millisecond execution.
            </p>

            {/* CTA Command Line */}
            <div className="mt-8 group">
              <div className="flex items-center gap-2 text-[#006600] text-xs mb-1">
                <Power className="h-3 w-3" />
                <span>ROOT ACCESS REQUIRED</span>
              </div>
              <button 
                onClick={login}
                className="w-full sm:w-auto flex items-center gap-4 bg-[#0a0a0a] border border-[#00ff00] px-6 py-4 hover:bg-[#00ff00] hover:text-black transition-all duration-300 group-hover:shadow-[0_0_20px_rgba(0,255,0,0.3)]"
              >
                <span className="text-xl font-bold">{">"} INITIALIZE_AGENT</span>
                <Play className="h-5 w-5 fill-current animate-pulse" />
              </button>
            </div>
          </div>

          {/* Mini Diagnostic Panel (Mobile only usually, but good here) */}
          <div className="grid grid-cols-3 gap-4 border-t border-[#1a1a1a] pt-6">
             <div>
                <div className="text-[10px] text-[#006600] uppercase mb-1">Total Volume</div>
                <div className="text-2xl font-bold text-[#00ff00]">$2.3M</div>
             </div>
             <div>
                <div className="text-[10px] text-[#006600] uppercase mb-1">Daily Trades</div>
                <div className="text-2xl font-bold text-[#00ff00]">1.2K</div>
             </div>
             <div>
                <div className="text-[10px] text-[#006600] uppercase mb-1">Success Rate</div>
                <div className="text-2xl font-bold text-[#00ff00]">94%</div>
             </div>
          </div>

        </div>

        {/* RIGHT COLUMN: TERMINAL & MODULES (5 cols) */}
        <div className="lg:col-span-5 flex flex-col gap-6">
          
          {/* Component 1: The Boot Log (Terminal) */}
          <div className="border border-[#1a1a1a] bg-[#050505] p-1 shadow-2xl">
            <div className="bg-[#111] px-2 py-1 flex items-center justify-between border-b border-[#1a1a1a]">
              <span className="text-[10px] text-[#006600]">boot_sequence.log</span>
              <div className="flex gap-1">
                <div className="w-2 h-2 rounded-full bg-[#333]" />
                <div className="w-2 h-2 rounded-full bg-[#333]" />
              </div>
            </div>
            <div className="p-4 font-mono text-xs h-[200px] overflow-hidden relative">
              {bootLog.map((line, i) => (
                <div key={i} className="mb-1 leading-tight">
                   {line.type === "cmd" && <span className="text-[#00ff00] font-bold">{line.text}</span>}
                   {line.type === "sys" && <span className="text-[#006600]">{line.text}</span>}
                   {line.type === "res" && <span className="text-[#00aa00] ml-2">{line.text}</span>}
                   {line.type === "success" && <span className="text-[#00ff00] bg-[#00ff00]/10 px-1 mt-2 inline-block">{line.text}</span>}
                </div>
              ))}
              <div className="absolute bottom-4 left-4 flex animate-pulse">
                <span className="text-[#00ff00] mr-1">{">"}</span>
                <span className="w-2 h-4 bg-[#00ff00]" />
              </div>
              {/* Scanline overlay */}
              <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] z-10 background-size-[100%_2px,3px_100%]" />
            </div>
          </div>

          {/* Component 2: Process Manager (Features) */}
          <div className="border border-[#1a1a1a] bg-[#050505] flex-1 min-h-[300px]">
             <div className="bg-[#111] px-3 py-2 border-b border-[#1a1a1a] flex justify-between items-center">
                <div className="flex items-center gap-2">
                   <Server className="h-3 w-3 text-[#00ff00]" />
                   <span className="text-[10px] font-bold text-[#00ff00] uppercase">Active Modules</span>
                </div>
                <span className="text-[10px] text-[#006600]">CPU: 12%</span>
             </div>
             
             <div className="divide-y divide-[#1a1a1a]">
                {/* Header Row */}
                <div className="grid grid-cols-12 px-3 py-1.5 text-[9px] text-[#004400] uppercase tracking-wider bg-[#080808]">
                   <div className="col-span-2">PID</div>
                   <div className="col-span-5">Process Name</div>
                   <div className="col-span-3">Status</div>
                   <div className="col-span-2 text-right">Load</div>
                </div>
                
                {/* Rows */}
                {systemProcesses.map((proc) => (
                   <div key={proc.pid} className="grid grid-cols-12 px-3 py-3 items-center hover:bg-[#111] transition-colors group cursor-default">
                      <div className="col-span-2 text-[10px] text-[#006600] font-mono group-hover:text-[#00ff00]">
                         {proc.pid}
                      </div>
                      <div className="col-span-5">
                         <div className="flex items-center gap-2">
                            <proc.icon className="h-3 w-3 text-[#00aa00]" />
                            <div>
                               <div className="text-[11px] font-bold text-[#eee] group-hover:text-[#00ff00]">{proc.name}</div>
                               <div className="text-[9px] text-[#555] hidden sm:block">{proc.cmd}</div>
                            </div>
                         </div>
                      </div>
                      <div className="col-span-3">
                         <span className={`text-[9px] px-1.5 py-0.5 rounded-sm ${
                            proc.status === "RUNNING" ? "bg-[#00ff00]/20 text-[#00ff00]" :
                            proc.status === "LOCKED" ? "bg-[#ff3333]/20 text-[#ff3333]" :
                            "bg-[#222] text-[#777]"
                         }`}>
                            {proc.status}
                         </span>
                      </div>
                      <div className="col-span-2 text-right text-[10px] text-[#00aa00] font-mono">
                         {proc.load}
                      </div>
                   </div>
                ))}
             </div>
          </div>

        </div>
      </main>

      {/* --- FOOTER: STATUS TICKER --- */}
      <footer className="border-t border-[#1a1a1a] bg-[#050505] py-2 overflow-hidden relative z-20">
         <div className="flex whitespace-nowrap animate-marquee">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center gap-8 mx-4">
                 <div className="flex items-center gap-2 text-[10px] text-[#006600]">
                    <Globe className="h-3 w-3" />
                    <span>NETWORK_LATENCY: 12ms</span>
                 </div>
                 <div className="flex items-center gap-2 text-[10px] text-[#006600]">
                    <ShieldCheck className="h-3 w-3" />
                    <span>SECURITY_LEVEL: MAXIMUM</span>
                 </div>
                 <div className="flex items-center gap-2 text-[10px] text-[#006600]">
                    <Activity className="h-3 w-3" />
                    <span>ACTIVE_NODES: 4,021</span>
                 </div>
                 <span className="text-[#1a1a1a]">///</span>
              </div>
            ))}
         </div>
      </footer>
    </div>
  );
}