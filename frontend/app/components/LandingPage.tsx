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
  TrendingUp
} from "lucide-react";

const features = [
  {
    icon: Cpu,
    command: "ai.analyze()",
    title: "Neural Analysis",
    description: "LLM-powered decision engine with real-time pattern recognition",
  },
  {
    icon: Activity,
    command: "data.stream()",
    title: "Live Data Feed",
    description: "OHLCV streams at 1-min intervals with 70+ indicators",
  },
  {
    icon: Database,
    command: "sentiment.scan()",
    title: "Sentiment Parser",
    description: "Multi-source social sentiment aggregation and scoring",
  },
  {
    icon: TrendingUp,
    command: "indicators.calc()",
    title: "Tech Analysis",
    description: "RSI, MACD, Bollinger Bands, Volume Profile, and more",
  },
  {
    icon: Zap,
    command: "agent.execute()",
    title: "Auto Execute",
    description: "24/7 autonomous trading via secure embedded wallets",
  },
  {
    icon: Lock,
    command: "wallet.secure()",
    title: "Vault Security",
    description: "Military-grade encryption for all wallet operations",
  },
];

const stats = [
  { label: "volume_traded", value: "2.3M", prefix: "$" },
  { label: "trades_daily", value: "1.2K", prefix: "" },
  { label: "success_rate", value: "94", prefix: "", suffix: "%" },
];

const codeLines = [
  { type: "comment", text: "// Initialize AI Trading Agent v2.1.0" },
  { type: "code", text: "const agent = new TradingAgent();" },
  { type: "code", text: "agent.connect('movement-mainnet');" },
  { type: "code", text: "agent.enableAutonomousMode();" },
  { type: "output", text: "[OK] Agent initialized successfully" },
  { type: "output", text: "[OK] Connected to Movement Network" },
  { type: "status", text: "Status: READY" },
];

export function LandingPage() {
  const { login } = usePrivyWallet();

  return (
    <div className="min-h-screen scanline">
      <section className="relative pt-16 pb-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto">
            <div className="terminal-window mb-12">
              <div className="terminal-header">
                <div className="terminal-dot red"></div>
                <div className="terminal-dot yellow"></div>
                <div className="terminal-dot green"></div>
                <span className="terminal-title">ai-trading-agent — bash</span>
              </div>
              <div className="terminal-body font-mono text-sm">
                {codeLines.map((line, i) => (
                  <div key={i} className="mb-1">
                    {line.type === "comment" && (
                      <span className="text-[#006600]">{line.text}</span>
                    )}
                    {line.type === "code" && (
                      <span className="text-[#00ff00]">
                        <span className="text-[#00aa00]">$ </span>
                        {line.text}
                      </span>
                    )}
                    {line.type === "output" && (
                      <span className="text-[#00cc00]">{line.text}</span>
                    )}
                    {line.type === "status" && (
                      <span className="text-[#00ff00] glow-text font-bold">{line.text}</span>
                    )}
                  </div>
                ))}
                <div className="mt-4 flex items-center">
                  <span className="text-[#00aa00]">$ </span>
                  <span className="text-[#00ff00]">_</span>
                  <span className="cursor"></span>
                </div>
              </div>
            </div>

            <div className="text-center mb-12">
              <div className="inline-flex items-center gap-3 px-4 py-2 border border-[#00ff00] mb-8">
                <span className="w-2 h-2 bg-[#00ff00] animate-pulse-terminal"></span>
                <span className="text-[#00ff00] text-sm uppercase tracking-widest">
                  [LIVE] Movement Network Mainnet
                </span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-[#00ff00] mb-6 tracking-tight glow-text">
                AI_TRADING_AGENT
              </h1>

              <p className="text-lg text-[#00aa00] mb-10 max-w-2xl mx-auto font-mono">
                {">"} Autonomous trading system powered by neural networks.
                <br />
                {">"} Real-time analysis. Intelligent execution. 24/7 uptime.
              </p>

              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Button 
                  size="lg" 
                  className="btn-terminal-filled px-8 py-6 text-base w-full sm:w-auto"
                  onClick={login}
                >
                  <Terminal className="h-5 w-5 mr-2" />
                  ./initialize --start
                </Button>
                <Button 
                  size="lg"
                  className="btn-terminal px-8 py-6 text-base w-full sm:w-auto"
                >
                  cat README.md
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-6 max-w-3xl mx-auto mb-8">
              {stats.map((stat) => (
                <div key={stat.label} className="stat-card text-center">
                  <div className="text-2xl sm:text-3xl font-bold text-[#00ff00] mb-2 font-mono glow-text-subtle">
                    {stat.prefix}{stat.value}{stat.suffix}
                  </div>
                  <div className="text-xs text-[#006600] font-mono uppercase tracking-wider">
                    {stat.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="divider" />
      </div>

      <section id="features" className="py-20">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-2xl sm:text-3xl font-bold text-[#00ff00] mb-4 font-mono">
              {"// SYSTEM MODULES"}
            </h2>
            <p className="text-[#006600] font-mono">
              Core components of the autonomous trading system
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-w-5xl mx-auto">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="p-5 bg-[#0f0f0f] border border-[#1a1a1a] hover:border-[#00ff00] transition-all group"
              >
                <div className="flex items-center gap-3 mb-3">
                  <feature.icon className="h-5 w-5 text-[#00ff00]" />
                  <code className="text-[#00aa00] text-sm">{feature.command}</code>
                </div>
                <h3 className="text-[#00ff00] font-bold mb-2 font-mono group-hover:glow-text-subtle">
                  {feature.title}
                </h3>
                <p className="text-[#006600] text-sm font-mono leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="divider" />
      </div>

      <section className="py-16">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mx-auto p-8 border border-[#00ff00] glow-border">
            <div className="flex flex-col md:flex-row items-center justify-between gap-6">
              <div className="font-mono">
                <div className="text-[#006600] text-sm mb-2">
                  {"// Ready to deploy?"}
                </div>
                <div className="text-[#00ff00] text-xl font-bold glow-text-subtle">
                  {">"} sudo ./start_trading
                </div>
              </div>
              <Button 
                size="lg" 
                className="btn-terminal-filled px-8 whitespace-nowrap"
                onClick={login}
              >
                EXECUTE
                <ArrowRight className="h-4 w-4 ml-2" />
              </Button>
            </div>
          </div>
        </div>
      </section>

      <footer className="py-8 border-t border-[#1a1a1a]">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center font-mono text-xs text-[#006600]">
            <p>AI Trading Agent v2.1.0 | Movement Network</p>
            <p className="mt-1">{"// All systems operational"}</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
