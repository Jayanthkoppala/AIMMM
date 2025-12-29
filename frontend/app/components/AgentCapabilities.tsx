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
  ChevronDown,
  ChevronRight
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

export function AgentCapabilities() {
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [pulseIndex, setPulseIndex] = useState(0);
  const [systemStatus, setSystemStatus] = useState<"online" | "syncing">("online");

  const agents: Agent[] = [
    {
      id: "ohlcv",
      name: "OHLCV Data Agent",
      shortName: "OHLCV",
      icon: BarChart3,
      status: "active",
      description: "Real-time 1-minute candle data collector",
      dataType: "Market Feed",
      outputType: "Candle[]",
      features: [
        "Real-time 1-minute price candles",
        "Volume analysis & tracking",
        "Support/resistance detection",
        "Price action pattern recognition"
      ],
      metrics: { uptime: "99.9%", latency: "45ms", requests: "1.2k/min" }
    },
    {
      id: "technical",
      name: "Technical Indicators Agent",
      shortName: "TECH",
      icon: TrendingUp,
      status: "active",
      description: "85+ technical indicators computation engine",
      dataType: "Candle[]",
      outputType: "Indicators{}",
      features: [
        "Momentum: RSI, StochRSI, TSI, UO, Williams %R, AO, KAMA, ROC",
        "Trend: SMA, EMA, MACD, ADX, Vortex, Ichimoku, Parabolic SAR",
        "Volatility: ATR, Bollinger Bands, Keltner, Donchian",
        "Volume: MFI, OBV, CMF, Force Index, VWAP"
      ],
      metrics: { uptime: "99.8%", latency: "120ms", requests: "850/min" }
    },
    {
      id: "sentiment",
      name: "Sentiment Analysis Agent",
      shortName: "SENT",
      icon: MessageSquare,
      status: "processing",
      description: "Multi-source sentiment aggregator",
      dataType: "Social Feed",
      outputType: "Sentiment{}",
      features: [
        "Twitter/X real-time analysis",
        "News sentiment scoring",
        "Whale movement tracking",
        "Fear & Greed Index"
      ],
      metrics: { uptime: "98.5%", latency: "2.1s", requests: "60/min" }
    },
    {
      id: "risk",
      name: "Risk Management Agent",
      shortName: "RISK",
      icon: AlertTriangle,
      status: "active",
      description: "Dynamic risk control & position sizing",
      dataType: "Strategy{}",
      outputType: "RiskParams{}",
      features: [
        "Dynamic position sizing by AI confidence",
        "Adaptive stop-loss (volatility-based)",
        "Take-profit optimization",
        "Drawdown protection"
      ],
      metrics: { uptime: "99.9%", latency: "15ms", requests: "200/min" }
    },
    {
      id: "llm",
      name: "LLM Decision Agent",
      shortName: "LLM",
      icon: Brain,
      status: "active",
      description: "Neural network trading decision engine",
      dataType: "AllData{}",
      outputType: "Signal{}",
      features: [
        "Multi-agent data synthesis",
        "Buy/Sell/Hold signal generation",
        "Confidence scoring (0-100%)",
        "Reasoning chain output"
      ],
      metrics: { uptime: "99.7%", latency: "1.8s", requests: "12/min" }
    },
    {
      id: "execution",
      name: "Execution Agent",
      shortName: "EXEC",
      icon: Activity,
      status: "idle",
      description: "DEX trade execution via Mosaic",
      dataType: "Signal{}",
      outputType: "Trade{}",
      features: [
        "Optimal route finding",
        "Slippage protection",
        "Paper trading simulation",
        "Real execution on Movement"
      ],
      metrics: { uptime: "99.9%", latency: "350ms", requests: "5/min" }
    }
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setPulseIndex((prev) => (prev + 1) % agents.length);
    }, 800);
    return () => clearInterval(interval);
  }, [agents.length]);

  useEffect(() => {
    const interval = setInterval(() => {
      setSystemStatus((prev) => prev === "online" ? "syncing" : "online");
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case "active": return "text-[#00ff00]";
      case "processing": return "text-[#ffff00]";
      case "idle": return "text-[#666666]";
      default: return "text-[#666666]";
    }
  };

  const getStatusBg = (status: string) => {
    switch (status) {
      case "active": return "bg-[#00ff00]";
      case "processing": return "bg-[#ffff00]";
      case "idle": return "bg-[#666666]";
      default: return "bg-[#666666]";
    }
  };

  return (
    <div className="space-y-6 relative">
      {/* System Header */}
      <div className="border border-[#00ff00]/30 bg-black p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Server className="h-6 w-6 text-[#00ff00]" />
              <div className="absolute -top-1 -right-1 w-2 h-2 bg-[#00ff00] rounded-full animate-pulse" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#00ff00] font-mono tracking-wider">
                AGENT_NETWORK_v2.1.0
              </h1>
              <p className="text-[10px] text-[#006600] font-mono">
                Autonomous Trading Intelligence System
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Radio className={`h-4 w-4 ${systemStatus === "online" ? "text-[#00ff00]" : "text-[#ffff00]"} ${systemStatus === "syncing" ? "animate-pulse" : ""}`} />
              <span className="text-xs font-mono text-[#00ff00]">
                {systemStatus === "online" ? "SYSTEM ONLINE" : "SYNCING..."}
              </span>
            </div>
            <div className="text-xs font-mono text-[#006600] border border-[#1a1a1a] px-2 py-1">
              6 AGENTS ACTIVE
            </div>
          </div>
        </div>
      </div>

      {/* Data Flow Pipeline Visualization */}
      <div className="border border-[#1a1a1a] bg-[#050505] p-4">
        <div className="flex items-center gap-2 mb-4">
          <Database className="h-4 w-4 text-[#00ff00]" />
          <span className="text-xs font-mono text-[#00ff00]">DATA_PIPELINE</span>
          <span className="text-[10px] font-mono text-[#006600] ml-auto">Real-time flow visualization</span>
        </div>
        
        {/* Pipeline Flow */}
        <div className="flex items-center justify-between overflow-x-auto py-4 px-2">
          {agents.map((agent, idx) => (
            <div key={agent.id} className="flex items-center">
              {/* Agent Node */}
              <div 
                className={`relative flex flex-col items-center cursor-pointer transition-all duration-300 ${
                  pulseIndex === idx ? "scale-110" : "scale-100"
                }`}
                onClick={() => setExpandedAgent(expandedAgent === agent.id ? null : agent.id)}
              >
                {/* Pulse ring */}
                {pulseIndex === idx && (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="w-14 h-14 border border-[#00ff00] rounded-full animate-ping opacity-30" />
                  </div>
                )}
                
                {/* Node circle */}
                <div className={`w-12 h-12 rounded-full border-2 flex items-center justify-center transition-all ${
                  expandedAgent === agent.id 
                    ? "border-[#00ff00] bg-[#00ff00]/20" 
                    : "border-[#1a1a1a] bg-black hover:border-[#00ff00]/50"
                }`}>
                  <agent.icon className={`h-5 w-5 ${getStatusColor(agent.status)}`} />
                </div>
                
                {/* Status indicator */}
                <div className={`absolute -bottom-1 -right-1 w-3 h-3 rounded-full border border-black ${getStatusBg(agent.status)} ${
                  agent.status === "processing" ? "animate-pulse" : ""
                }`} />
                
                {/* Label */}
                <span className={`text-[10px] font-mono mt-2 ${
                  expandedAgent === agent.id ? "text-[#00ff00]" : "text-[#006600]"
                }`}>
                  {agent.shortName}
                </span>
              </div>
              
              {/* Connection Arrow */}
              {idx < agents.length - 1 && (
                <div className="flex items-center mx-2">
                  <div className={`h-[2px] w-8 transition-colors duration-300 ${
                    pulseIndex === idx ? "bg-[#00ff00]" : "bg-[#1a1a1a]"
                  }`} />
                  <Zap className={`h-3 w-3 mx-1 transition-colors duration-300 ${
                    pulseIndex === idx ? "text-[#00ff00]" : "text-[#1a1a1a]"
                  }`} />
                  <div className={`h-[2px] w-8 transition-colors duration-300 ${
                    pulseIndex === idx ? "bg-[#00ff00]" : "bg-[#1a1a1a]"
                  }`} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Agent Details Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        {agents.map((agent, idx) => (
          <div
            key={agent.id}
            className={`border transition-all duration-300 cursor-pointer ${
              expandedAgent === agent.id 
                ? "border-[#00ff00] bg-[#0a0a0a]" 
                : "border-[#1a1a1a] bg-black hover:border-[#00ff00]/30"
            }`}
            onClick={() => setExpandedAgent(expandedAgent === agent.id ? null : agent.id)}
          >
            {/* Agent Header */}
            <div className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 border ${
                    expandedAgent === agent.id ? "border-[#00ff00] bg-[#00ff00]/10" : "border-[#1a1a1a]"
                  }`}>
                    <agent.icon className={`h-5 w-5 ${getStatusColor(agent.status)}`} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold font-mono text-[#00ff00]">
                        {agent.name}
                      </h3>
                      <span className={`text-[9px] font-mono px-1.5 py-0.5 border ${
                        agent.status === "active" ? "border-[#00ff00]/50 text-[#00ff00]" :
                        agent.status === "processing" ? "border-[#ffff00]/50 text-[#ffff00]" :
                        "border-[#666666]/50 text-[#666666]"
                      }`}>
                        {agent.status.toUpperCase()}
                      </span>
                    </div>
                    <p className="text-[10px] text-[#006600] font-mono mt-0.5">
                      {agent.description}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-1 text-[#006600]">
                  {expandedAgent === agent.id ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </div>
              </div>

              {/* Data Flow Info */}
              <div className="flex items-center gap-2 mt-3 text-[10px] font-mono">
                <span className="text-[#666666]">IN:</span>
                <span className="text-[#00ff00]/70 px-1.5 py-0.5 bg-[#00ff00]/5 border border-[#1a1a1a]">
                  {agent.dataType}
                </span>
                <ArrowRight className="h-3 w-3 text-[#006600]" />
                <span className="text-[#666666]">OUT:</span>
                <span className="text-[#00ff00]/70 px-1.5 py-0.5 bg-[#00ff00]/5 border border-[#1a1a1a]">
                  {agent.outputType}
                </span>
              </div>
            </div>

            {/* Expanded Content */}
            {expandedAgent === agent.id && (
              <div className="border-t border-[#1a1a1a] p-4 space-y-4">
                {/* Metrics */}
                <div className="flex gap-4">
                  <div className="flex-1 p-2 bg-black border border-[#1a1a1a]">
                    <div className="text-[9px] text-[#666666] font-mono">UPTIME</div>
                    <div className="text-sm text-[#00ff00] font-mono font-bold">{agent.metrics.uptime}</div>
                  </div>
                  <div className="flex-1 p-2 bg-black border border-[#1a1a1a]">
                    <div className="text-[9px] text-[#666666] font-mono">LATENCY</div>
                    <div className="text-sm text-[#00ff00] font-mono font-bold">{agent.metrics.latency}</div>
                  </div>
                  <div className="flex-1 p-2 bg-black border border-[#1a1a1a]">
                    <div className="text-[9px] text-[#666666] font-mono">REQUESTS</div>
                    <div className="text-sm text-[#00ff00] font-mono font-bold">{agent.metrics.requests}</div>
                  </div>
                </div>

                {/* Features */}
                <div>
                  <div className="text-[10px] text-[#666666] font-mono mb-2">CAPABILITIES</div>
                  <div className="space-y-1.5">
                    {agent.features.map((feature, featIdx) => (
                      <div key={featIdx} className="flex items-start gap-2">
                        <span className="text-[#00ff00] text-[10px] font-mono">$</span>
                        <span className="text-[11px] text-[#006600] font-mono leading-relaxed">
                          {feature}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* System Console */}
      <div className="border border-[#1a1a1a] bg-black">
        {/* Console Header */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-[#1a1a1a] bg-[#0a0a0a]">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#febc2e]" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
          </div>
          <span className="text-[10px] text-[#666666] font-mono ml-2">system_console — bash</span>
        </div>
        
        {/* Console Content */}
        <div className="p-4 font-mono text-[11px] space-y-1">
          <div className="text-[#006600]">
            <span className="text-[#00ff00]">$</span> cat /etc/agent_network/config.md
          </div>
          <div className="text-[#006600] mt-2">
            ╔══════════════════════════════════════════════════════════════╗
          </div>
          <div className="text-[#006600]">
            ║  <span className="text-[#00ff00]">AGENT NETWORK CONFIGURATION</span>                                ║
          </div>
          <div className="text-[#006600]">
            ╠══════════════════════════════════════════════════════════════╣
          </div>
          <div className="text-[#006600]">
            ║  Network: Movement Mainnet                                   ║
          </div>
          <div className="text-[#006600]">
            ║  DEX: Mosaic Aggregator                                      ║
          </div>
          <div className="text-[#006600]">
            ║  Data: 1-min candles + 24h sentiment                         ║
          </div>
          <div className="text-[#006600]">
            ║  Capital: $1000 (paper) / Connected wallet (live)            ║
          </div>
          <div className="text-[#006600]">
            ╚══════════════════════════════════════════════════════════════╝
          </div>
          <div className="mt-3 text-[#006600]">
            <span className="text-[#00ff00]">$</span> ./start_trading --mode=autonomous
          </div>
          <div className="text-[#006600]">
            [INFO] Navigate to <span className="text-[#00ff00]">./strategies</span> to create your first strategy
          </div>
          <div className="text-[#006600]">
            [INFO] All agents will coordinate automatically based on your description
          </div>
          <div className="flex items-center gap-1 mt-1">
            <span className="text-[#00ff00]">$</span>
            <span className="w-2 h-4 bg-[#00ff00] animate-pulse" />
          </div>
        </div>
      </div>

      {/* Quick Stats Footer */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3 border border-[#1a1a1a] bg-black">
          <div className="flex items-center gap-2 mb-1">
            <Cpu className="h-3.5 w-3.5 text-[#00ff00]" />
            <span className="text-[9px] text-[#666666] font-mono">PROCESSING</span>
          </div>
          <div className="text-lg text-[#00ff00] font-mono font-bold">85+</div>
          <div className="text-[9px] text-[#006600] font-mono">Indicators</div>
        </div>
        <div className="p-3 border border-[#1a1a1a] bg-black">
          <div className="flex items-center gap-2 mb-1">
            <Database className="h-3.5 w-3.5 text-[#00ff00]" />
            <span className="text-[9px] text-[#666666] font-mono">DATA POINTS</span>
          </div>
          <div className="text-lg text-[#00ff00] font-mono font-bold">2.5k+</div>
          <div className="text-[9px] text-[#006600] font-mono">Candles stored</div>
        </div>
        <div className="p-3 border border-[#1a1a1a] bg-black">
          <div className="flex items-center gap-2 mb-1">
            <Zap className="h-3.5 w-3.5 text-[#00ff00]" />
            <span className="text-[9px] text-[#666666] font-mono">LATENCY</span>
          </div>
          <div className="text-lg text-[#00ff00] font-mono font-bold">&lt;2s</div>
          <div className="text-[9px] text-[#006600] font-mono">Decision time</div>
        </div>
        <div className="p-3 border border-[#1a1a1a] bg-black">
          <div className="flex items-center gap-2 mb-1">
            <Radio className="h-3.5 w-3.5 text-[#00ff00]" />
            <span className="text-[9px] text-[#666666] font-mono">UPTIME</span>
          </div>
          <div className="text-lg text-[#00ff00] font-mono font-bold">99.9%</div>
          <div className="text-[9px] text-[#006600] font-mono">System availability</div>
        </div>
      </div>
    </div>
  );
}
