"use client";

import { useState, useEffect } from "react";
import { 
  Brain, 
  TrendingUp, 
  BarChart3, 
  MessageSquare, 
  Activity, 
  AlertTriangle, 
  Cpu, 
  Zap, 
  Radio, 
  Server, 
  Database, 
  ArrowRight, 
  Terminal,
  Wifi,
  Workflow,
  Code,
  Lock
} from "lucide-react";

interface Agent {
  id: string;
  name: string;
  shortName: string;
  icon: React.ElementType;
  status: "active" | "processing" | "idle";
  description: string;
  dataType: string;
  outputType: string;
  features: string[];
  metrics: {
    uptime: string;
    latency: string;
    requests: string;
  };
}

// --- DECORATIVE UI COMPONENTS ---
const Hexagon = ({ className }: { className?: string }) => (
  <svg viewBox="0 0 100 100" className={className} fill="currentColor">
    <polygon points="50 0, 93 25, 93 75, 50 100, 7 75, 7 25" />
  </svg>
);

const ConnectionLine = ({ active }: { active: boolean }) => (
  <div className="hidden md:flex items-center flex-1 mx-2 relative h-1 bg-[#1a1a1a] overflow-hidden rounded-full">
    {active && (
      <div className="absolute inset-0 bg-[#00ff00] animate-progress-indeterminate shadow-[0_0_10px_#00ff00]" />
    )}
  </div>
);

export function AgentCapabilities() {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [pulseIndex, setPulseIndex] = useState(0);
  const [consoleLines, setConsoleLines] = useState<string[]>([
    "[SYSTEM] Initializing Agent Network...",
    "[NET] Connecting to Movement Mainnet...",
    "[AUTH] Secure handshake established."
  ]);

  const agents: Agent[] = [
    {
      id: "ohlcv",
      name: "OHLCV Collector",
      shortName: "DATA",
      icon: BarChart3,
      status: "active",
      description: "Real-time 1m candle ingestion",
      dataType: "Market Feed",
      outputType: "Candle[]",
      features: ["Price Normalization", "Volume Analysis", "Gap Detection"],
      metrics: { uptime: "99.9%", latency: "45ms", requests: "1.2k/m" }
    },
    {
      id: "technical",
      name: "Indicator Engine",
      shortName: "TECH",
      icon: TrendingUp,
      status: "active",
      description: "Compute 85+ technicals",
      dataType: "Candle[]",
      outputType: "Indicators{}",
      features: ["RSI/MACD/Bollinger", "Trend Identification", "Volatility Scans"],
      metrics: { uptime: "99.8%", latency: "120ms", requests: "850/m" }
    },
    {
      id: "sentiment",
      name: "Sentiment AI",
      shortName: "SENT",
      icon: MessageSquare,
      status: "processing",
      description: "Social & News NLP analysis",
      dataType: "Social Feed",
      outputType: "Sentiment{}",
      features: ["Whale Alert Tracking", "Fear/Greed Index", "Viral Topic Detection"],
      metrics: { uptime: "98.5%", latency: "2.1s", requests: "60/m" }
    },
    {
      id: "risk",
      name: "Risk Guardian",
      shortName: "RISK",
      icon: AlertTriangle,
      status: "active",
      description: "Position sizing & safety",
      dataType: "Strategy{}",
      outputType: "RiskParams{}",
      features: ["Max Drawdown Control", "Volatility Sizing", "Exposure Limits"],
      metrics: { uptime: "99.9%", latency: "15ms", requests: "200/m" }
    },
    {
      id: "llm",
      name: "Neural Core",
      shortName: "BRAIN",
      icon: Brain,
      status: "active",
      description: "Final decision synthesis",
      dataType: "AggregatedData",
      outputType: "Signal{}",
      features: ["Multi-Agent Reasoning", "Signal Confidence", "Trade Logic Gen"],
      metrics: { uptime: "99.7%", latency: "1.8s", requests: "12/m" }
    },
    {
      id: "execution",
      name: "Executor",
      shortName: "EXEC",
      icon: Activity,
      status: "idle",
      description: "On-chain routing & signing",
      dataType: "Signal{}",
      outputType: "TxHash",
      features: ["Gas Optimization", "Slippage Protection", "MEV Guard"],
      metrics: { uptime: "99.9%", latency: "350ms", requests: "5/m" }
    }
  ];

  // Animation for the "Pulse" traveling through the pipeline
  useEffect(() => {
    const interval = setInterval(() => {
      setPulseIndex((prev) => (prev + 1) % (agents.length + 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [agents.length]);

  // Console log simulator
  useEffect(() => {
    const interval = setInterval(() => {
      const logs = [
        `[DATA] Candle close: $${(Math.random() * 2000 + 1000).toFixed(2)}`,
        `[TECH] RSI(14) updated: ${(Math.random() * 100).toFixed(2)}`,
        `[RISK] Position check passed. Exposure < 5%`,
        `[SENT] New whale alert processed.`,
        `[EXEC] Mempool scan complete.`,
        `[LLM] Analyzing context window...`
      ];
      const randomLog = logs[Math.floor(Math.random() * logs.length)];
      setConsoleLines(prev => [...prev.slice(-4), `${new Date().toLocaleTimeString()} ${randomLog}`]);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-4">
      
      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* 1. HEADER & SYSTEM STATUS */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-4 bg-[#0a0a0a] border border-[#1a1a1a] relative overflow-hidden">
        {/* Striped Background */}
        <div className="absolute inset-0 bg-[repeating-linear-gradient(45deg,transparent,transparent_10px,#111_10px,#111_20px)] opacity-50" />
        
        <div className="relative z-10 flex items-center gap-4">
          <div className="relative">
            <div className="absolute inset-0 bg-[#00ff00] blur-md opacity-20 animate-pulse" />
            <div className="w-12 h-12 border-2 border-[#00ff00] bg-black flex items-center justify-center">
              <Workflow className="h-6 w-6 text-[#00ff00]" />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold font-mono text-white tracking-widest">
              AIMMM<span className="text-[#00ff00]">_SWARM</span>
            </h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="w-2 h-2 rounded-full bg-[#00ff00] animate-pulse" />
              <span className="text-[10px] font-mono text-[#006600]">ORCHESTRATION LAYER: ONLINE</span>
            </div>
          </div>
        </div>

        <div className="relative z-10 flex gap-2">
          <div className="px-3 py-1 bg-black border border-[#1a1a1a] flex items-center gap-2">
             <Wifi className="h-3 w-3 text-[#00ff00]" />
             <span className="text-[10px] font-mono text-[#666]">PING: 14ms</span>
          </div>
          <div className="px-3 py-1 bg-black border border-[#1a1a1a] flex items-center gap-2">
             <Database className="h-3 w-3 text-[#00ff00]" />
             <span className="text-[10px] font-mono text-[#666]">SYNCED</span>
          </div>
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* 2. CIRCUIT VISUALIZATION (Desktop Only) */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      <div className="hidden md:flex bg-[#050505] border border-[#1a1a1a] p-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(0,255,0,0.03),transparent_70%)]" />
        
        <div className="relative z-10 w-full flex items-center justify-between">
          {agents.map((agent, idx) => (
            <div key={agent.id} className="flex items-center flex-1 last:flex-none">
              
              {/* Node */}
              <button 
                onClick={() => setExpandedAgent(expandedAgent === agent.id ? null : agent.id)}
                className={`group relative flex flex-col items-center transition-all duration-300 ${
                  expandedAgent === agent.id ? 'scale-110' : 'hover:scale-105'
                }`}
              >
                {/* Hexagon Status Ring */}
                <div className={`w-14 h-14 relative flex items-center justify-center transition-all ${
                   agent.status === 'processing' ? 'animate-pulse' : ''
                }`}>
                   <Hexagon className={`absolute inset-0 ${
                     expandedAgent === agent.id 
                       ? 'text-[#00ff00]' 
                       : pulseIndex === idx 
                         ? 'text-[#00ff00]/50' 
                         : 'text-[#1a1a1a] group-hover:text-[#333]'
                   }`} />
                   <agent.icon className={`h-5 w-5 relative z-10 ${
                      expandedAgent === agent.id ? 'text-black' : 'text-[#666] group-hover:text-[#00ff00]'
                   }`} />
                </div>
                
                <span className={`text-[10px] font-mono mt-2 font-bold transition-colors ${
                  expandedAgent === agent.id ? 'text-[#00ff00]' : 'text-[#444] group-hover:text-[#666]'
                }`}>
                  {agent.shortName}
                </span>
                
                {/* Activity Indicator Dot */}
                {pulseIndex === idx && (
                  <div className="absolute -top-1 right-0 w-2 h-2 bg-[#00ff00] rounded-full shadow-[0_0_5px_#00ff00]" />
                )}
              </button>

              {/* Connector */}
              {idx < agents.length - 1 && (
                <ConnectionLine active={pulseIndex === idx} />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* 3. SERVER BLADE GRID */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {agents.map((agent) => (
          <div
            key={agent.id}
            onClick={() => setExpandedAgent(expandedAgent === agent.id ? null : agent.id)}
            className={`cursor-pointer border transition-all duration-300 overflow-hidden ${
              expandedAgent === agent.id 
                ? "border-[#00ff00] bg-[#0a0a0a]" 
                : "border-[#1a1a1a] bg-[#050505] hover:border-[#333]"
            }`}
          >
            {/* Header Row */}
            <div className="flex items-stretch h-16">
              {/* Status Bar Indicator */}
              <div className={`w-1 ${
                agent.status === 'active' ? 'bg-[#00ff00]' : 
                agent.status === 'processing' ? 'bg-[#ffff00]' : 'bg-[#333]'
              }`} />

              {/* Icon Box */}
              <div className="w-16 flex items-center justify-center bg-[#080808] border-r border-[#1a1a1a]">
                 <agent.icon className={`h-6 w-6 ${
                    expandedAgent === agent.id ? 'text-[#00ff00]' : 'text-[#444]'
                 }`} />
              </div>

              {/* Info Area */}
              <div className="flex-1 flex items-center justify-between px-4">
                 <div>
                    <h3 className="text-sm font-bold font-mono text-white flex items-center gap-2">
                       {agent.name}
                       {agent.status === 'processing' && <Loader2 className="h-3 w-3 animate-spin text-[#ffff00]" />}
                    </h3>
                    <p className="text-[10px] font-mono text-[#666]">{agent.description}</p>
                 </div>
                 
                 {/* Mini Metrics */}
                 <div className="hidden sm:flex flex-col items-end gap-1">
                    <div className="flex items-center gap-1.5 px-1.5 py-0.5 bg-[#111] rounded border border-[#222]">
                       <span className="w-1.5 h-1.5 rounded-full bg-[#00ff00]" />
                       <span className="text-[9px] font-mono text-[#888]">{agent.metrics.uptime}</span>
                    </div>
                 </div>
              </div>
            </div>

            {/* Expanded Details Panel */}
            {expandedAgent === agent.id && (
               <div className="border-t border-[#1a1a1a] p-4 bg-[#080808] animate-in slide-in-from-top-2 duration-200">
                  <div className="grid grid-cols-2 gap-4 mb-4">
                     <div className="space-y-1">
                        <span className="text-[9px] text-[#444] font-mono uppercase">Input Stream</span>
                        <div className="flex items-center gap-2 text-xs font-mono text-[#00ff00] bg-[#00ff00]/5 p-1 border border-[#00ff00]/20">
                           <Database className="h-3 w-3" />
                           {agent.dataType}
                        </div>
                     </div>
                     <div className="space-y-1">
                        <span className="text-[9px] text-[#444] font-mono uppercase">Output Stream</span>
                        <div className="flex items-center gap-2 text-xs font-mono text-[#00ff00] bg-[#00ff00]/5 p-1 border border-[#00ff00]/20">
                           <ArrowRight className="h-3 w-3" />
                           {agent.outputType}
                        </div>
                     </div>
                  </div>

                  <div className="space-y-2">
                     <span className="text-[9px] text-[#444] font-mono uppercase">Module Capabilities</span>
                     <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {agent.features.map((feat, i) => (
                           <div key={i} className="flex items-center gap-2 text-[10px] font-mono text-[#ccc]">
                              <Zap className="h-3 w-3 text-[#666]" />
                              {feat}
                           </div>
                        ))}
                     </div>
                  </div>
               </div>
            )}
          </div>
        ))}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* 4. SYSTEM CONSOLE & HUD */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
         
         {/* Live Logs Terminal */}
         <div className="lg:col-span-2 bg-black border border-[#1a1a1a] flex flex-col h-[200px] font-mono text-xs">
            <div className="flex items-center justify-between px-3 py-1.5 bg-[#111] border-b border-[#1a1a1a]">
               <div className="flex items-center gap-2">
                  <Terminal className="h-3 w-3 text-[#00ff00]" />
                  <span className="text-[#666] text-[10px]">daemon.log</span>
               </div>
               <span className="w-2 h-2 bg-[#00ff00] animate-pulse rounded-full" />
            </div>
            <div className="flex-1 p-3 overflow-hidden flex flex-col justify-end">
               {consoleLines.map((line, i) => (
                  <div key={i} className="text-[#006600] animate-in slide-in-from-left-2 fade-in duration-300">
                     <span className="text-[#003300] mr-2">$</span>
                     {line}
                  </div>
               ))}
               <div className="h-4 w-2 bg-[#00ff00] animate-pulse mt-1" />
            </div>
         </div>

         {/* HUD Stats */}
         <div className="bg-[#0a0a0a] border border-[#1a1a1a] p-4 flex flex-col justify-between">
            <div>
               <div className="flex items-center gap-2 mb-4">
                  <Activity className="h-4 w-4 text-[#00ff00]" />
                  <span className="text-xs font-mono text-white tracking-widest">SYSTEM_HEALTH</span>
               </div>
               
               <div className="space-y-4">
                  <div>
                     <div className="flex justify-between text-[10px] font-mono text-[#666] mb-1">
                        <span>CPU LOAD</span>
                        <span>24%</span>
                     </div>
                     <div className="h-1 bg-[#1a1a1a] w-full">
                        <div className="h-full bg-[#00ff00]" style={{ width: '24%' }} />
                     </div>
                  </div>
                  <div>
                     <div className="flex justify-between text-[10px] font-mono text-[#666] mb-1">
                        <span>MEMORY</span>
                        <span>6.2GB / 16GB</span>
                     </div>
                     <div className="h-1 bg-[#1a1a1a] w-full">
                        <div className="h-full bg-[#00ff00]" style={{ width: '38%' }} />
                     </div>
                  </div>
                  <div>
                     <div className="flex justify-between text-[10px] font-mono text-[#666] mb-1">
                        <span>NETWORK</span>
                        <span>1.2 MB/s</span>
                     </div>
                     <div className="h-1 bg-[#1a1a1a] w-full">
                        <div className="h-full bg-[#00ff00] animate-pulse" style={{ width: '15%' }} />
                     </div>
                  </div>
               </div>
            </div>
            
            <div className="mt-4 pt-4 border-t border-[#1a1a1a] flex items-center justify-between text-[10px] font-mono">
               <span className="text-[#444]">VERSION: 2.1.0</span>
               <div className="flex items-center gap-1 text-[#00ff00]">
                  <Lock className="h-3 w-3" />
                  SECURE
               </div>
            </div>
         </div>
      </div>

    </div>
  );
}

// Helper needed for the types (simple mock for the example)
const Loader2 = ({ className }: { className?: string }) => (
  <svg className={className} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>
);