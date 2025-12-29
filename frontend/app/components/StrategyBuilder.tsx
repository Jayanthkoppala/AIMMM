"use client";

import { useState, useEffect } from "react";
import { usePrivyWallet } from "@/app/hooks/use-privy-wallet";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import {
  Plus,
  Loader2,
  Sparkles,
  AlertCircle
} from "lucide-react";
import { 
  createStrategy,
  Strategy
} from "@/app/lib/api";

export function StrategyBuilder() {
  const { authenticated, getAccessToken } = usePrivyWallet();
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Form state for creating new strategy
  const [strategyName, setStrategyName] = useState("");
  const [strategyDescription, setStrategyDescription] = useState("");
  const [selectedPoolId, setSelectedPoolId] = useState<number>(2); // Default to USDC.e/MOVE pool (id: 2)
  const [tradingMode, setTradingMode] = useState<"paper" | "real">("paper");
  const [executionInterval, setExecutionInterval] = useState<number>(5); // Default 5 minutes
  const [selectedModel, setSelectedModel] = useState<string>("deepseek/deepseek-r1");
  
  // Dynamic risk parameters (ranges)
  const [perTradeMin, setPerTradeMin] = useState("50");
  const [perTradeMax, setPerTradeMax] = useState("200");
  const [stopLossMin, setStopLossMin] = useState("5");
  const [stopLossMax, setStopLossMax] = useState("15");
  const [takeProfitMin, setTakeProfitMin] = useState("10");
  const [takeProfitMax, setTakeProfitMax] = useState("30");
  const [maxConcurrentTrades, setMaxConcurrentTrades] = useState("5");

  
  const STATIC_POOLS = [
    { 
      id: 1, 
      name: "USDC.e / WETH.e Pool", 
      tokens: ["USDC.e", "WETH.e"],
      pool_address: "0x83193fdc4d23fca53b2a36aef082886f4ef1c345a2c721b31c6e90a51173014d"
    },
    { 
      id: 2, 
      name: "USDC.e / MOVE Pool", 
      tokens: ["USDC.e", "MOVE"],
      pool_address: "0xbcbf55e1004687d412f05856ef7c17dcaacc1be632ba2d67b71073d25b425c3b"
    }
  ];

  const EXECUTION_INTERVALS = [
    { value: 1, label: "1 minute" },
    { value: 5, label: "5 minutes" },
    { value: 15, label: "15 minutes" },
    { value: 30, label: "30 minutes" },
    { value: 60, label: "1 hour" },
  ];

  const LLM_MODELS = [
    { value: "openai/o1", label: "o1", provider: "OpenAI", badge: "Reasoning" },
    { value: "anthropic/claude-opus-4.1", label: "Claude Opus 4.1", provider: "Anthropic", badge: "Latest" },
    { value: "google/gemini-2.0-flash-thinking-exp", label: "Gemini 2.0 Thinking", provider: "Google", badge: "Reasoning" },
    { value: "deepseek/deepseek-r1", label: "DeepSeek R1", provider: "DeepSeek", badge: "Reasoning" },
    { value: "qwen/qwq-32b-preview", label: "QwQ 32B", provider: "Qwen", badge: "Reasoning" },
    { value: "x-ai/grok-2-1212", label: "Grok 2", provider: "xAI", badge: "Latest" },
  ];

  // Function to navigate to agents tab
  const navigateToAgents = () => {
    if (typeof window !== 'undefined') {
      const event = new CustomEvent('navigateToTab', { detail: 'agents' });
      window.dispatchEvent(event);
    }
  };

  const handleCreateStrategy = async () => {
    if (!strategyName.trim()) {
      alert("Please enter a strategy name");
      return;
    }

    try {
      setLoading(true);
      const token = authenticated ? await getAccessToken() : undefined;

      const selectedPool = STATIC_POOLS.find(p => p.id === selectedPoolId);
      const tokens = selectedPool?.tokens || [];

      const newStrategy = await createStrategy(
        {
          name: strategyName,
          description: strategyDescription || null,
          visibility: "private",
          is_active: false,
          execution_interval: executionInterval,
          pool_id: selectedPoolId,
          pool_address: selectedPool?.pool_address || selectedPoolId,
          strategy_config: {
            agent_configs: {
              ohlcv: {
                tokens,
                timeframes: ["1m"],
                dataPoints: 100,
              },
              technical: {
                timeframe: "1m",
                indicators: [
                  {
                    name: "rsi",
                    parameters: {
                      period: 14,
                      overbought: 70,
                      oversold: 30,
                    },
                    trigger_points: {
                      buy: "rsi < 30",
                      sell: "rsi > 70",
                    },
                  },
                ],
              },
            },
            paper_trading_config: {
              initial_capital_usdc: 1000,
              capital_per_trade: parseFloat(perTradeMin), // Using min as base
              max_concurrent_positions: parseInt(maxConcurrentTrades) || 5,
              stop_loss_pct: parseFloat(stopLossMin) / 100, // Using min as base
              take_profit_pct: parseFloat(takeProfitMin) / 100, // Using min as base
              // Store ranges for LLM decision making
              per_trade_range: {
                min: parseFloat(perTradeMin),
                max: parseFloat(perTradeMax)
              },
              stop_loss_range: {
                min: parseFloat(stopLossMin) / 100,
                max: parseFloat(stopLossMax) / 100
              },
              take_profit_range: {
                min: parseFloat(takeProfitMin) / 100,
                max: parseFloat(takeProfitMax) / 100
              },
              trading_mode: tradingMode
            },
            llm_provider: selectedModel,
          },
        },
        token || undefined
      );

      // Reset form
      setStrategyName("");
      setStrategyDescription("");
      setShowCreateForm(false);
      
      // Navigate to My Strategies tab after creation
      if (typeof window !== 'undefined') {
        const event = new CustomEvent('navigateToTab', { detail: 'my-strategies' });
        window.dispatchEvent(event);
      }
    } catch (error) {
      console.error("Failed to create strategy:", error);
      alert("Failed to create strategy. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[#00ff00] font-mono glow-text">
            ./strategy_builder
          </h1>
          <p className="text-xs text-[#006600] mt-1 font-mono">
            {">"} AI-powered trading strategies on Movement Network
          </p>
        </div>
        <Button
          onClick={() => setShowCreateForm(!showCreateForm)}
          className="bg-[#00ff00] text-black hover:bg-[#00cc00] font-mono text-xs"
        >
          <Plus className="h-4 w-4 mr-2" />
          {showCreateForm ? "CANCEL" : "NEW_STRATEGY"}
        </Button>
      </div>
          {/* Info Banner */}
          <div className="p-3 bg-black border border-[#00ff00]/50 rounded">
              <div className="flex items-start gap-2">
                <AlertCircle className="h-4 w-4 text-[#00ff00] flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-[10px] text-[#006600] font-mono mb-2 leading-relaxed">
                    <span className="text-[#00ff00]">TIP:</span> Learn about available technical indicators, sentiment data, and agent capabilities in the{" "}
                    <button
                      onClick={navigateToAgents}
                      className="text-[#00ff00] hover:text-[#00cc00] underline"
                    >
                      ./agents
                    </button>
                    {" "}tab before writing your strategy.
                  </p>
                  <p className="text-[10px] text-[#006600] font-mono leading-relaxed">
                    <span className="text-[#00ff00]">Examples:</span> RSI, MACD, Bollinger Bands, Twitter sentiment, whale movements, etc.
                  </p>
                </div>
              </div>
            </div>

      {/* Create Strategy Form */}
      {showCreateForm && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* LEFT SIDE - Simplified Configuration */}
          <div className="space-y-6 p-6 bg-[#0a0a0a] border border-[#1a1a1a]">
            <div className="flex items-center gap-2 pb-3 border-b border-[#1a1a1a]">
              <Sparkles className="h-4 w-4 text-[#00ff00]" />
              <span className="text-sm font-mono text-[#00ff00]">CONFIGURATION</span>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label className="text-xs text-[#006600] uppercase font-mono">
                  {">"} Strategy Name
                </Label>
                <Input
                  value={strategyName}
                  onChange={(e) => setStrategyName(e.target.value)}
                  placeholder="My Trading Strategy"
                  className="bg-black border-[#1a1a1a] text-[#00ff00] focus:border-[#00ff00] font-mono"
                />
              </div>

              <div className="h-px bg-gradient-to-r from-transparent via-[#00ff00]/30 to-transparent" />

              <div className="space-y-2">
                <Label className="text-xs text-[#006600] uppercase font-mono">
                  {">"} Trading Pool
                </Label>
                <select
                  value={selectedPoolId}
                  onChange={(e) => setSelectedPoolId(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-black border border-[#1a1a1a] text-[#00ff00] text-xs focus:border-[#00ff00] focus:outline-none font-mono"
                >
                  {STATIC_POOLS.map((pool) => (
                    <option key={pool.id} value={pool.id}>
                      {pool.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="h-px bg-gradient-to-r from-transparent via-[#00ff00]/30 to-transparent" />

              <div className="space-y-2">
                <Label className="text-xs text-[#006600] uppercase font-mono">
                  {">"} Trading Mode
                </Label>
                <select
                  value={tradingMode}
                  onChange={(e) => setTradingMode(e.target.value as "paper" | "real")}
                  className="w-full px-3 py-2 bg-black border border-[#1a1a1a] text-[#00ff00] text-xs focus:border-[#00ff00] focus:outline-none font-mono"
                >
                  <option value="paper">Paper Trading (Simulation)</option>
                  <option value="real">Real Trading (Live)</option>
                </select>
              </div>

              <div className="h-px bg-gradient-to-r from-transparent via-[#00ff00]/30 to-transparent" />

              <div className="space-y-2">
                <Label className="text-xs text-[#006600] uppercase font-mono">
                  {">"} Execution Interval
                </Label>
                <select
                  value={executionInterval}
                  onChange={(e) => setExecutionInterval(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-black border border-[#1a1a1a] text-[#00ff00] text-xs focus:border-[#00ff00] focus:outline-none font-mono"
                >
                  {EXECUTION_INTERVALS.map((interval) => (
                    <option key={interval.value} value={interval.value}>
                      Every {interval.label}
                    </option>
                  ))}
                </select>
                <p className="text-[9px] text-[#004400] font-mono">
                  How often the AI will analyze and execute trades
                </p>
              </div>

              <div className="h-px bg-gradient-to-r from-transparent via-[#00ff00]/30 to-transparent" />

              <div className="space-y-2">
                <Label className="text-xs text-[#006600] uppercase font-mono">
                  {">"} AI Model
                </Label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full px-3 py-2 bg-black border border-[#1a1a1a] text-[#00ff00] text-xs focus:border-[#00ff00] focus:outline-none font-mono"
                >
                  {LLM_MODELS.map((model) => (
                    <option key={model.value} value={model.value}>
                      {model.label} ({model.provider}) - [{model.badge}]
                    </option>
                  ))}
                </select>
                <p className="text-[9px] text-[#004400] font-mono">
                  Select the AI model for trading decisions
                </p>
              </div>

              <div className="h-px bg-gradient-to-r from-transparent via-[#00ff00]/30 to-transparent" />

              {/* Dynamic Risk Parameters */}
              <div className="space-y-3">
                <div className="text-xs text-[#00ff00] uppercase font-mono mb-2">
                  {">"} Dynamic Risk Parameters (AI adjusts within range)
                </div>

                {/* Per Trade Range */}
                <div className="space-y-2">
                  <Label className="text-[10px] text-[#006600] font-mono">
                    Per Trade Amount ($)
                  </Label>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <span className="text-[9px] text-[#006600] font-mono">Min</span>
                      <Input
                        type="number"
                        value={perTradeMin}
                        onChange={(e) => setPerTradeMin(e.target.value)}
                        placeholder="50"
                        className="bg-black border-[#1a1a1a] text-[#00ff00] focus:border-[#00ff00] font-mono text-xs"
                      />
                    </div>
                    <div className="space-y-1">
                      <span className="text-[9px] text-[#006600] font-mono">Max</span>
                      <Input
                        type="number"
                        value={perTradeMax}
                        onChange={(e) => setPerTradeMax(e.target.value)}
                        placeholder="200"
                        className="bg-black border-[#1a1a1a] text-[#00ff00] focus:border-[#00ff00] font-mono text-xs"
                      />
                    </div>
                  </div>
                </div>

                {/* Stop Loss Range */}
                <div className="space-y-2">
                  <Label className="text-[10px] text-[#006600] font-mono">
                    Stop Loss (%)
                  </Label>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <span className="text-[9px] text-[#006600] font-mono">Min</span>
                      <Input
                        type="number"
                        value={stopLossMin}
                        onChange={(e) => setStopLossMin(e.target.value)}
                        placeholder="5"
                        className="bg-black border-[#1a1a1a] text-[#00ff00] focus:border-[#00ff00] font-mono text-xs"
                      />
                    </div>
                    <div className="space-y-1">
                      <span className="text-[9px] text-[#006600] font-mono">Max</span>
                      <Input
                        type="number"
                        value={stopLossMax}
                        onChange={(e) => setStopLossMax(e.target.value)}
                        placeholder="15"
                        className="bg-black border-[#1a1a1a] text-[#00ff00] focus:border-[#00ff00] font-mono text-xs"
                      />
                    </div>
                  </div>
                </div>

                {/* Take Profit Range */}
                <div className="space-y-2">
                  <Label className="text-[10px] text-[#006600] font-mono">
                    Take Profit (%)
                  </Label>
                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <span className="text-[9px] text-[#006600] font-mono">Min</span>
                      <Input
                        type="number"
                        value={takeProfitMin}
                        onChange={(e) => setTakeProfitMin(e.target.value)}
                        placeholder="10"
                        className="bg-black border-[#1a1a1a] text-[#00ff00] focus:border-[#00ff00] font-mono text-xs"
                      />
                    </div>
                    <div className="space-y-1">
                      <span className="text-[9px] text-[#006600] font-mono">Max</span>
                      <Input
                        type="number"
                        value={takeProfitMax}
                        onChange={(e) => setTakeProfitMax(e.target.value)}
                        placeholder="30"
                        className="bg-black border-[#1a1a1a] text-[#00ff00] focus:border-[#00ff00] font-mono text-xs"
                      />
                    </div>
                  </div>
                </div>

                {/* Max Concurrent Trades */}
                <div className="space-y-2">
                  <Label className="text-[10px] text-[#006600] font-mono">
                    Max Concurrent Trades
                  </Label>
                  <Input
                    type="number"
                    value={maxConcurrentTrades}
                    onChange={(e) => setMaxConcurrentTrades(e.target.value)}
                    placeholder="5"
                    min="1"
                    max="20"
                    className="bg-black border-[#1a1a1a] text-[#00ff00] focus:border-[#00ff00] font-mono text-xs"
                  />
                  <p className="text-[9px] text-[#004400] font-mono">
                    Maximum number of open positions at once
                  </p>
                </div>

                <div className="text-[9px] text-[#006600] font-mono italic p-2 bg-black/50 border border-[#1a1a1a]">
                  * AI adjusts these values based on confidence level and market conditions
                </div>
              </div>

              <div className="p-4 bg-black/50 border border-[#1a1a1a] rounded">
                <div className="text-[10px] text-[#006600] font-mono mb-2">FIXED SETTINGS:</div>
                <div className="grid grid-cols-2 gap-2 text-[10px] text-[#006600] font-mono">
                  <div>• Initial Capital: $1000</div>
                  <div>• RSI: 14/30/70</div>
                  <div>• Data: 1m candles</div>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT SIDE - Description */}
          <div className="space-y-6 p-6 bg-[#0a0a0a] border border-[#1a1a1a]">
            <div className="flex items-center gap-2 pb-3 border-b border-[#1a1a1a]">
              <AlertCircle className="h-4 w-4 text-[#00ff00]" />
              <span className="text-sm font-mono text-[#00ff00]">STRATEGY_DESCRIPTION</span>
            </div>

        

            <div className="space-y-4 h-full flex flex-col">
              <Label className="text-xs text-[#006600] uppercase font-mono">
                {">"} Describe your trading strategy in detail
              </Label>
              <textarea
                value={strategyDescription}
                onChange={(e) => setStrategyDescription(e.target.value)}
                placeholder="Enter detailed strategy description...&#10;&#10;Example:&#10;This strategy uses RSI indicator to identify oversold and overbought conditions.&#10;- BUY when RSI < 30 (oversold)&#10;- SELL when RSI > 70 (overbought)&#10;- Stop loss at 5% to limit downside&#10;- Take profit at 10% for consistent gains"
                className="flex-1 min-h-[400px] p-4 bg-black border border-[#1a1a1a] text-[#00ff00] focus:border-[#00ff00] focus:outline-none font-mono text-xs resize-none"
              />

              <Button
                onClick={handleCreateStrategy}
                disabled={loading || !strategyName.trim()}
                className="w-full bg-[#00ff00] text-black hover:bg-[#00cc00] font-mono text-xs disabled:opacity-50"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    CREATING...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    CREATE_STRATEGY
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
