"use client";

import { 
  Brain, 
  TrendingUp, 
  BarChart3, 
  MessageSquare,
  Activity,
  AlertTriangle,
  Info
} from "lucide-react";

export function AgentCapabilities() {
  const agents = [
    {
      name: "OHLCV Data Agent",
      icon: BarChart3,
      description: "1-minute candle data (Open, High, Low, Close, Volume)",
      features: [
        "Real-time 1-minute price candles",
        "Volume analysis",
        "Support and resistance levels",
        "Price action patterns"
      ]
    },
    {
      name: "Technical Indicators Agent",
      icon: TrendingUp,
      description: "Technical analysis indicators on 1-minute candles",
      features: [
        "Momentum: RSI, Stochastic RSI (StochRSI), TSI, Ultimate Oscillator (UO), Stochastic, Williams %R, Awesome Oscillator (AO), KAMA, ROC, PPO, PVO",
        "Trend: SMA (20/50/200), EMA (12/26/50), WMA, MACD, ADX, Vortex (VI), TRIX, Mass Index, CCI, DPO, KST, Ichimoku, Parabolic SAR (PSAR), STC, Aroon",
        "Volatility: ATR, Bollinger Bands (BB), Keltner Channel (KC), Donchian Channel (DC), Ulcer Index (UI)",
        "Volume: MFI, ADI, OBV, CMF, Force Index (FI), EOM, VPT, NVI, VWAP",
        "Other: Daily Return, Log Return, Cumulative Return, Volume SMA"
      ]
    },
    {
      name: "Sentiment Analysis Agent",
      icon: MessageSquare,
      description: "One-day sentiment data from social media and news",
      features: [
        "Twitter/X sentiment (last 24 hours)",
        "News sentiment analysis",
        "On-chain whale movements",
        "Fear & Greed Index"
      ]
    },
    {
      name: "Risk Management Agent",
      icon: AlertTriangle,
      description: "Dynamic risk control based on AI confidence",
      features: [
        "Position sizing: Set MIN-MAX range, AI adjusts by confidence",
        "Stop loss: Set MIN-MAX %, AI adjusts by volatility",
        "Take profit: Set MIN-MAX %, AI adjusts by trend strength",
        "Paper Trading: $1000 virtual capital",
        "Real Trading: Live wallet execution"
      ]
    },
    {
      name: "LLM Decision Agent",
      icon: Brain,
      description: "GPT-4 powered trading decisions",
      features: [
        "Analyzes all agent data",
        "Generates buy/sell/hold signals",
        "Confidence scoring (0-100%)",
        "Dynamic risk parameter adjustment"
      ]
    },
    {
      name: "Execution Agent",
      icon: Activity,
      description: "DEX execution via Mosaic aggregator",
      features: [
        "Best price routing",
        "Slippage protection",
        "Paper trading simulation",
        "Real trading execution"
      ]
    }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[#00ff00] font-mono glow-text">
          ./agent_capabilities
        </h1>
        <p className="text-xs text-[#006600] mt-1 font-mono">
          {">"} AI agents powering your trading strategies
        </p>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {agents.map((agent, idx) => (
          <div
            key={idx}
            className="p-5 bg-[#0a0a0a] border border-[#1a1a1a] hover:border-[#00ff00]/50 transition-all"
          >
            <div className="flex items-start gap-3 mb-4">
              <div className="p-2 bg-black border border-[#1a1a1a]">
                <agent.icon className="h-5 w-5 text-[#00ff00]" />
              </div>
              <div className="flex-1">
                <h2 className="text-base font-bold font-mono mb-1 text-[#00ff00]">
                  {agent.name}
                </h2>
                <p className="text-xs text-[#006600] font-mono mb-3">
                  {agent.description}
                </p>
              </div>
            </div>

            <div className="space-y-1.5 ml-11">
              {agent.features.map((feature, featIdx) => (
                <div key={featIdx} className="flex items-start gap-2">
                  <span className="text-[#00ff00] text-xs font-mono mt-0.5">•</span>
                  <span className="text-xs text-[#006600] font-mono leading-relaxed">
                    {feature}
                  </span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* How to Use */}
      <div className="p-5 bg-[#0a0a0a] border border-[#00ff00]">
        <div className="flex items-start gap-3">
          <Info className="h-5 w-5 text-[#00ff00] flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="text-sm font-bold text-[#00ff00] font-mono mb-3">
              HOW TO USE
            </h3>
            <div className="space-y-1.5 text-xs text-[#006600] font-mono leading-relaxed">
              <p>1. Go to <span className="text-[#00ff00]">./strategies</span> tab</p>
              <p>2. Write strategy description mentioning indicators/data you want</p>
              <p>3. Example: "Use RSI &lt; 30 to buy. Check MACD for confirmation. Use Twitter sentiment from last 24h."</p>
              <p>4. LLM coordinates all agents automatically</p>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Reference */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-black border border-[#1a1a1a]">
          <h4 className="text-xs font-bold text-[#00ff00] font-mono mb-2">FIXED</h4>
          <div className="space-y-1 text-[10px] text-[#006600] font-mono">
            <div>• Capital: $1000</div>
            <div>• Max Positions: 5</div>
            <div>• Candles: 1-minute</div>
            <div>• Sentiment: 1-day</div>
          </div>
        </div>

        <div className="p-4 bg-black border border-[#1a1a1a]">
          <h4 className="text-xs font-bold text-[#00ff00] font-mono mb-2">DYNAMIC</h4>
          <div className="space-y-1 text-[10px] text-[#006600] font-mono">
            <div>• Per Trade: MIN-MAX range</div>
            <div>• Stop Loss: MIN-MAX %</div>
            <div>• Take Profit: MIN-MAX %</div>
            <div>• AI adjusts by confidence</div>
          </div>
        </div>

        <div className="p-4 bg-black border border-[#1a1a1a]">
          <h4 className="text-xs font-bold text-[#00ff00] font-mono mb-2">EXECUTION</h4>
          <div className="space-y-1 text-[10px] text-[#006600] font-mono">
            <div>• Paper/Real Trading</div>
            <div>• Network: Movement</div>
            <div>• DEX: Mosaic</div>
          </div>
        </div>
      </div>
    </div>
  );
}
