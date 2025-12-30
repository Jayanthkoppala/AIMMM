"use client";

import { useState } from "react";
import { usePrivyWallet } from "@/app/hooks/use-privy-wallet";
import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { createStrategy } from "@/app/lib/api";
import { Button } from "@/app/components/ui/button";
import { Input } from "@/app/components/ui/input";
import { Label } from "@/app/components/ui/label";
import {
  Plus,
  Loader2,
  Sparkles,
  AlertCircle,
  Brain,
  Shield,
  Zap,
  ArrowRight,
  Terminal,
  Cpu,
  Activity,
  Code,
  Lock,
  PlayCircle,
  Disc,
  Clock
} from "lucide-react";

// --- DECORATIVE COMPONENTS ---
const Corner = ({ className = "" }: { className?: string }) => (
  <div className={`absolute w-3 h-3 border-t border-l border-[#00ff00] ${className}`} />
);

const Scanline = () => (
  <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] z-0 bg-[length:100%_2px,3px_100%] opacity-20" />
);

export function StrategyBuilder() {
  const { authenticated, getAccessToken } = usePrivyWallet();
  const { account } = useWallet();
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // Form state
  const [strategyName, setStrategyName] = useState("");
  const [strategyDescription, setStrategyDescription] = useState("");
  const [selectedPoolId, setSelectedPoolId] = useState<number>(2);
  const [tradingMode, setTradingMode] = useState<"paper" | "real">("paper");
  const [executionInterval, setExecutionInterval] = useState<number>(5);
  const [selectedModel, setSelectedModel] = useState<string>("deepseek/deepseek-r1");
  
  const [perTradeMin, setPerTradeMin] = useState("50");
  const [perTradeMax, setPerTradeMax] = useState("200");
  const [stopLossMin, setStopLossMin] = useState("5");
  const [stopLossMax, setStopLossMax] = useState("15");
  const [takeProfitMin, setTakeProfitMin] = useState("10");
  const [takeProfitMax, setTakeProfitMax] = useState("30");
  const [maxConcurrentTrades, setMaxConcurrentTrades] = useState("5");

  // Helper: Get wallet address or session ID
  const getWalletAddress = (): string | undefined => {
    if (account?.address) {
      const walletAddr = typeof account.address === "string" 
        ? account.address 
        : (account.address?.toString ? account.address.toString() : String(account.address));
      
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('aimmm_session_id');
      }
      return walletAddr;
    }
    
    if (typeof window !== 'undefined') {
      const existingSessionId = sessionStorage.getItem('aimmm_session_id');
      if (existingSessionId) {
        return existingSessionId;
      }
      const newSessionId = `session-${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
      sessionStorage.setItem('aimmm_session_id', newSessionId);
      return newSessionId;
    }
    
    return undefined;
  };

  const STATIC_POOLS = [
    { 
      id: 1, 
      name: "USDC.e / WETH.e", 
      tokens: ["USDC.e", "WETH.e"],
      tradingToken: "WETH-USDC", // Trading token (non-USDC) for OHLCV
      liquidity: "$4.2M"
    },
    { 
      id: 2, 
      name: "USDC.e / MOVE", 
      tokens: ["USDC.e", "MOVE"],
      tradingToken: "MOVE-USDC", // Trading token (non-USDC) for OHLCV
      liquidity: "$12.5M"
    }
  ];

  const EXECUTION_INTERVALS = [
    { value: 1, label: "1m" },
    { value: 5, label: "5m" },
    { value: 15, label: "15m" },
    { value: 30, label: "30m" },
    { value: 60, label: "1h" },
  ];

  const LLM_MODELS = [
    { value: "deepseek/deepseek-r1", label: "DeepSeek R1", provider: "DeepSeek", badge: "REC", cost: "Low" },
    { value: "anthropic/claude-opus-4.1", label: "Claude Opus", provider: "Anthropic", badge: "MAX", cost: "High" },
    { value: "openai/o1", label: "OpenAI o1", provider: "OpenAI", badge: "STD", cost: "Med" },
  ];

  const handleCreateStrategy = async () => {
    if (!strategyName.trim()) {
      alert("Please enter a strategy name");
      return;
    }
    
    if (!strategyDescription.trim()) {
      alert("Please describe your strategy logic");
      return;
    }

    try {
      setLoading(true);
      
      // Get authentication details
      const token = authenticated ? await getAccessToken() : undefined;
      const walletAddressRaw = getWalletAddress();
      // Ensure walletAddress is never null (sessionStorage.getItem can return null)
      // TypeScript sees sessionStorage.getItem as potentially returning null, so we need to filter it out
      const walletAddress: string | undefined = walletAddressRaw ?? undefined;

      // Get the trading token for the selected pool (non-USDC token)
      const selectedPool = STATIC_POOLS.find(p => p.id === selectedPoolId);
      const tradingToken = selectedPool?.tradingToken || "MOVE-USDC"; // Default to MOVE-USDC if pool not found
      
      console.log(`[StrategyBuilder] Selected pool: ${selectedPool?.name}, Trading token: ${tradingToken}`);
      
      // Build strategy data
      const strategyData = {
        name: strategyName,
        description: strategyDescription,
        visibility: "private" as const,
        is_active: false,
        pool_id: selectedPoolId,
        pool_address: undefined,
        execution_interval: executionInterval,
        strategy_config: {
          agent_configs: {
            ohlcv: {
              tokens: [tradingToken], // Use the trading token from selected pool (WETH-USDC or MOVE-USDC)
              timeframes: ["1m", "5m", "15m"],
              dataPoints: 200
            },
            technical: {
              timeframe: "1m",
              indicators: [
                {
                  name: "RSI",
                  parameters: { period: 14 },
                  trigger_points: { oversold: "30", overbought: "70" }
                },
                {
                  name: "MACD",
                  parameters: { fast: 12, slow: 26, signal: 9 },
                  trigger_points: undefined
                },
                {
                  name: "MA",
                  parameters: { period: 200, type: "SMA" },
                  trigger_points: undefined
                }
              ]
            },
            sentiment: {
              enabled: true,
              weight: 0.3
            }
          },
          paper_trading_config: {
            initial_capital_usdc: 10000,
            capital_per_trade: parseFloat(perTradeMax),
            max_concurrent_positions: parseInt(maxConcurrentTrades),
            position_sizing_strategy: "fixed" as const,
            max_position_pct: 0.2,
            stop_loss_pct: parseFloat(stopLossMax) / 100,
            take_profit_pct: parseFloat(takeProfitMax) / 100
          },
          llm_provider: selectedModel
        }
      };

      console.log("Creating strategy with data:", strategyData);
      console.log("Auth token:", token ? "present" : "none");
      console.log("Wallet address:", walletAddress);

      // TypeScript workaround: ensure walletAddress is never null
      // The type guard above should have filtered out null, but TypeScript doesn't narrow it properly
      // Use explicit undefined if null
      const safeWalletAddress: string | undefined = (walletAddress === null || walletAddress === undefined) ? undefined : walletAddress;
      const result = await createStrategy(strategyData, token, safeWalletAddress);
      
      console.log("Strategy created successfully:", result);
      
      // Reset form
      setStrategyName("");
      setStrategyDescription("");
      setShowCreateForm(false);
      
      alert("Strategy created successfully! Check 'My Strategies' to view it.");
      
      // Optionally trigger a reload of strategies if needed
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('strategy-created'));
      }
    } catch (error) {
      console.error("Failed to create strategy:", error);
      alert(error instanceof Error ? error.message : "Failed to create strategy. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  // ═══════════════════════════════════════════════════════════════════
  // VIEW 1: THE BLUEPRINT LANDING
  // ═══════════════════════════════════════════════════════════════════
  if (!showCreateForm) {
    return (
      <div className="relative min-h-[600px] flex items-center justify-center p-4 bg-[#050505]">
        <Scanline />
        
        {/* Decorative Grid Background */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#111_1px,transparent_1px),linear-gradient(to_bottom,#111_1px,transparent_1px)] bg-[size:40px_40px] opacity-50" />

        <div className="relative z-10 max-w-2xl w-full">
          <div className="border border-[#1a1a1a] bg-[#0a0a0a]/90 backdrop-blur-md p-1">
            <div className="border border-[#00ff00]/20 p-8 flex flex-col items-center text-center relative overflow-hidden">
              {/* Corner Decorations */}
              <Corner className="top-0 left-0" />
              <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-[#00ff00]" />
              <div className="absolute bottom-0 left-0 w-3 h-3 border-b border-l border-[#00ff00]" />
              <div className="absolute bottom-0 right-0 w-3 h-3 border-b border-r border-[#00ff00]" />

              <div className="w-16 h-16 bg-[#00ff00]/10 rounded-full flex items-center justify-center mb-6 animate-pulse border border-[#00ff00]/30">
                <Brain className="h-8 w-8 text-[#00ff00]" />
              </div>

              <h1 className="text-3xl font-bold text-white font-mono mb-2 tracking-tighter">
                STRATEGY<span className="text-[#00ff00]">_</span>BUILDER
              </h1>
              <p className="text-[#666] font-mono text-sm mb-8 max-w-md">
                Initialize a new autonomous trading agent. define logic, set risk parameters, and deploy to the Movement Network.
              </p>

              <div className="grid grid-cols-2 gap-4 w-full mb-8">
                <div className="bg-[#111] border border-[#222] p-4 text-left group hover:border-[#00ff00]/30 transition-colors cursor-default">
                  <div className="flex items-center gap-2 mb-2">
                    <Terminal className="h-4 w-4 text-[#00ff00]" />
                    <span className="text-xs font-mono text-[#fff]">NATURAL LANGUAGE</span>
                  </div>
                  <p className="text-[10px] text-[#666] font-mono leading-relaxed">
                    Describe your edge in plain English. The LLM translates intent into execution logic.
                  </p>
                </div>
                <div className="bg-[#111] border border-[#222] p-4 text-left group hover:border-[#00ff00]/30 transition-colors cursor-default">
                  <div className="flex items-center gap-2 mb-2">
                    <Shield className="h-4 w-4 text-[#00ff00]" />
                    <span className="text-xs font-mono text-[#fff]">RISK GUARDRAILS</span>
                  </div>
                  <p className="text-[10px] text-[#666] font-mono leading-relaxed">
                    Hard-coded exit protocols ensuring your agent stays within safety bounds.
                  </p>
                </div>
              </div>

              <Button
                onClick={() => setShowCreateForm(true)}
                className="group relative px-8 py-6 bg-[#00ff00] text-black hover:bg-[#00cc00] font-mono font-bold tracking-widest overflow-hidden"
              >
                <span className="relative z-10 flex items-center gap-2">
                  <PlayCircle className="h-5 w-5" />
                  INITIALIZE_SYSTEM
                </span>
                <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════
  // VIEW 2: THE COCKPIT FORM
  // ═══════════════════════════════════════════════════════════════════
  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Top Bar */}
      <div className="flex items-center justify-between bg-[#0a0a0a] border border-[#1a1a1a] p-3">
        <div className="flex items-center gap-3">
           <div className="flex items-center gap-1.5 px-2 py-1 bg-[#00ff00]/10 border border-[#00ff00]/30">
              <div className="w-1.5 h-1.5 rounded-full bg-[#00ff00] animate-pulse" />
              <span className="text-[10px] font-mono text-[#00ff00] font-bold">SYSTEM_ACTIVE</span>
           </div>
           <span className="text-xs font-mono text-[#666]">
              // CONFIGURE NEW AGENT
           </span>
        </div>
        <Button
          onClick={() => setShowCreateForm(false)}
          variant="ghost"
          className="h-6 text-[10px] font-mono text-[#666] hover:text-[#00ff00]"
        >
          [ ABORT ]
        </Button>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
        
        {/* LEFT COLUMN: HARDWARE & ENVIRONMENT (4 Cols) */}
        <div className="lg:col-span-4 space-y-4">
          
          {/* 1. Identity Module */}
          <div className="bg-[#050505] border border-[#1a1a1a] p-4 relative group">
            <Corner className="top-0 left-0" />
            <div className="mb-4">
              <Label className="text-[9px] text-[#006600] font-mono mb-1 uppercase tracking-widest">Designation</Label>
              <Input
                value={strategyName}
                onChange={(e) => setStrategyName(e.target.value)}
                placeholder="ENTER_STRATEGY_NAME"
                className="bg-black border-0 border-b border-[#333] rounded-none px-0 text-[#00ff00] focus:border-[#00ff00] font-mono text-sm placeholder:text-[#333] focus:ring-0"
              />
            </div>

            <div className="mb-4">
               <Label className="text-[9px] text-[#006600] font-mono mb-2 uppercase tracking-widest block">Trading Mode</Label>
               <div className="flex bg-[#111] p-1 border border-[#222]">
                  {(['paper', 'real'] as const).map(mode => (
                     <button
                        key={mode}
                        onClick={() => setTradingMode(mode)}
                        className={`flex-1 py-1.5 text-[10px] font-mono uppercase transition-all ${
                           tradingMode === mode 
                           ? 'bg-[#00ff00] text-black font-bold' 
                           : 'text-[#666] hover:text-white'
                        }`}
                     >
                        {mode}
                     </button>
                  ))}
               </div>
            </div>
          </div>

          {/* 2. Intelligence Module */}
          <div className="bg-[#050505] border border-[#1a1a1a] p-4">
            <div className="flex items-center gap-2 mb-3 border-b border-[#1a1a1a] pb-2">
              <Cpu className="h-3 w-3 text-[#00ff00]" />
              <span className="text-xs font-mono text-white">NEURAL_CORE</span>
            </div>
            
            <div className="space-y-2">
              {LLM_MODELS.map((model) => (
                <div 
                  key={model.value}
                  onClick={() => setSelectedModel(model.value)}
                  className={`cursor-pointer p-2 border transition-all ${
                    selectedModel === model.value
                    ? 'bg-[#00ff00]/5 border-[#00ff00] opacity-100'
                    : 'bg-[#0a0a0a] border-[#222] hover:border-[#444] opacity-60'
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span className={`text-xs font-mono ${selectedModel === model.value ? 'text-[#00ff00]' : 'text-[#ccc]'}`}>
                      {model.label}
                    </span>
                    <span className="text-[9px] px-1.5 bg-[#111] text-[#666] border border-[#222] font-mono">
                      {model.badge}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 3. Environment Module */}
          <div className="bg-[#050505] border border-[#1a1a1a] p-4">
            <div className="flex items-center gap-2 mb-3 border-b border-[#1a1a1a] pb-2">
              <Activity className="h-3 w-3 text-[#00ff00]" />
              <span className="text-xs font-mono text-white">TARGET_MARKET</span>
            </div>

            <div className="space-y-3">
              <div>
                 <Label className="text-[9px] text-[#666] font-mono mb-1 block">LIQUIDITY POOL</Label>
                 <div className="grid grid-cols-1 gap-2">
                    {STATIC_POOLS.map(pool => (
                       <button
                          key={pool.id}
                          onClick={() => setSelectedPoolId(pool.id)}
                          className={`flex items-center justify-between px-3 py-2 border text-left ${
                             selectedPoolId === pool.id
                             ? 'bg-[#00ff00]/10 border-[#00ff00] text-[#00ff00]'
                             : 'bg-black border-[#222] text-[#666]'
                          }`}
                       >
                          <div className="flex items-center gap-2">
                             <Disc className={`h-3 w-3 ${selectedPoolId === pool.id ? 'animate-spin-slow' : ''}`} />
                             <span className="text-[10px] font-mono">{pool.name}</span>
                          </div>
                       </button>
                    ))}
                 </div>
              </div>

              <div>
                 <Label className="text-[9px] text-[#666] font-mono mb-1 block">DECISION INTERVAL</Label>
                 <div className="flex flex-wrap gap-1">
                    {EXECUTION_INTERVALS.map(int => (
                       <button
                          key={int.value}
                          onClick={() => setExecutionInterval(int.value)}
                          className={`px-2 py-1 text-[10px] font-mono border ${
                             executionInterval === int.value
                             ? 'bg-[#00ff00] text-black border-[#00ff00]'
                             : 'bg-black text-[#666] border-[#222] hover:border-[#444]'
                          }`}
                       >
                          {int.label}
                       </button>
                    ))}
                 </div>
              </div>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: LOGIC & RISK (8 Cols) */}
        <div className="lg:col-span-8 flex flex-col gap-4 h-full">
          
          {/* 1. Logic Editor (The "IDE") */}
          <div className="flex-1 min-h-[300px] bg-[#080808] border border-[#1a1a1a] flex flex-col relative group hover:border-[#00ff00]/20 transition-colors">
            {/* Editor Header */}
            <div className="flex items-center justify-between px-3 py-2 bg-[#111] border-b border-[#1a1a1a]">
               <div className="flex items-center gap-2">
                  <Code className="h-3 w-3 text-[#00ff00]" />
                  <span className="text-xs font-mono text-[#ccc]">main_logic.txt</span>
               </div>
               <div className="flex gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-[#ff5f56]" />
                  <div className="w-2 h-2 rounded-full bg-[#ffbd2e]" />
                  <div className="w-2 h-2 rounded-full bg-[#27ca40]" />
               </div>
            </div>

            {/* Editor Body */}
            <div className="flex-1 flex relative">
               {/* Line Numbers */}
               <div className="w-8 py-3 bg-[#0a0a0a] border-r border-[#1a1a1a] text-right pr-2 select-none">
                  {[1,2,3,4,5,6,7,8,9,10,11,12].map(n => (
                     <div key={n} className="text-[10px] font-mono text-[#333] leading-5">{n}</div>
                  ))}
               </div>
               
               {/* Text Area */}
               <textarea
                  value={strategyDescription}
                  onChange={(e) => setStrategyDescription(e.target.value)}
                  placeholder="// Describe your trading strategy here...&#10;// Example:&#10;// If RSI < 30 and Price > MA(200) then BUY&#10;// The AI will interpret this logic against real-time data."
                  className="flex-1 w-full h-full bg-[#050505] text-[#00ff00] p-3 font-mono text-xs leading-5 resize-none border-none focus:ring-0 placeholder:text-[#004400]"
                  spellCheck={false}
               />
               
               {/* Flashing Cursor effect overlay (visual only) */}
               {!strategyDescription && (
                  <div className="absolute top-3 left-3 pointer-events-none">
                     <span className="text-[#004400] text-xs font-mono">// Awaiting input</span>
                     <span className="w-2 h-4 bg-[#00ff00] inline-block ml-1 animate-pulse align-middle" />
                  </div>
               )}
            </div>
            
            {/* Status Bar */}
            <div className="bg-[#00ff00]/5 border-t border-[#1a1a1a] px-3 py-1 flex items-center justify-between">
               <span className="text-[9px] font-mono text-[#006600]">Ln {strategyDescription.split('\n').length}, Col 1</span>
               <span className="text-[9px] font-mono text-[#006600]">UTF-8</span>
            </div>
          </div>

          {/* 2. Safety Protocols (Control Panel) */}
          <div className="bg-[#111] border border-[#1a1a1a] p-4 relative overflow-hidden">
             {/* Background Stripes */}
             <div className="absolute right-0 top-0 bottom-0 w-8 bg-[repeating-linear-gradient(45deg,#000,#000_10px,#1a1a1a_10px,#1a1a1a_20px)] opacity-20 pointer-events-none" />

             <div className="flex items-center gap-2 mb-4">
                <Shield className="h-4 w-4 text-[#00ff00]" />
                <span className="text-xs font-mono text-white tracking-widest">SAFETY_PROTOCOLS</span>
                <div className="h-px bg-[#333] flex-1 ml-2" />
             </div>

             <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
                
                {/* Protocol 1: Capital */}
                <div className="space-y-2">
                   <Label className="text-[9px] text-[#666] font-mono uppercase">Trade Size ($USD)</Label>
                   <div className="flex items-center gap-2 bg-black border border-[#333] p-1 px-2 rounded-sm">
                      <span className="text-[10px] text-[#444] font-mono">MIN</span>
                      <Input 
                         value={perTradeMin} 
                         onChange={(e) => setPerTradeMin(e.target.value)}
                         className="h-6 w-full bg-transparent border-none text-center font-mono text-[#00ff00] p-0 text-xs focus:ring-0" 
                      />
                      <span className="text-[#333]">-</span>
                      <Input 
                         value={perTradeMax} 
                         onChange={(e) => setPerTradeMax(e.target.value)}
                         className="h-6 w-full bg-transparent border-none text-center font-mono text-[#00ff00] p-0 text-xs focus:ring-0" 
                      />
                      <span className="text-[10px] text-[#444] font-mono">MAX</span>
                   </div>
                </div>

                {/* Protocol 2: Stop Loss */}
                <div className="space-y-2">
                   <Label className="text-[9px] text-[#666] font-mono uppercase">Stop Loss (%)</Label>
                   <div className="flex items-center gap-2 bg-black border border-[#333] p-1 px-2 rounded-sm">
                      <div className="w-1.5 h-1.5 bg-[#ff3333] rounded-full" />
                      <Input 
                         value={stopLossMin} 
                         onChange={(e) => setStopLossMin(e.target.value)}
                         className="h-6 w-full bg-transparent border-none text-right font-mono text-[#ff3333] p-0 text-xs focus:ring-0" 
                      />
                      <span className="text-[#333] text-xs">%</span>
                      <span className="text-[#333] mx-1">to</span>
                      <Input 
                         value={stopLossMax} 
                         onChange={(e) => setStopLossMax(e.target.value)}
                         className="h-6 w-full bg-transparent border-none text-left font-mono text-[#ff3333] p-0 text-xs focus:ring-0" 
                      />
                      <span className="text-[#333] text-xs">%</span>
                   </div>
                </div>

                {/* Protocol 3: Take Profit */}
                <div className="space-y-2">
                   <Label className="text-[9px] text-[#666] font-mono uppercase">Take Profit (%)</Label>
                   <div className="flex items-center gap-2 bg-black border border-[#333] p-1 px-2 rounded-sm">
                      <div className="w-1.5 h-1.5 bg-[#00ff00] rounded-full" />
                      <Input 
                         value={takeProfitMin} 
                         onChange={(e) => setTakeProfitMin(e.target.value)}
                         className="h-6 w-full bg-transparent border-none text-right font-mono text-[#00ff00] p-0 text-xs focus:ring-0" 
                      />
                      <span className="text-[#333] text-xs">%</span>
                      <span className="text-[#333] mx-1">to</span>
                      <Input 
                         value={takeProfitMax} 
                         onChange={(e) => setTakeProfitMax(e.target.value)}
                         className="h-6 w-full bg-transparent border-none text-left font-mono text-[#00ff00] p-0 text-xs focus:ring-0" 
                      />
                      <span className="text-[#333] text-xs">%</span>
                   </div>
                </div>
             </div>
          </div>

          {/* Action Button */}
          <Button
              onClick={handleCreateStrategy}
              disabled={loading || !strategyName.trim() || !strategyDescription.trim()}
              className="w-full bg-[#00ff00] text-black hover:bg-[#00cc00] font-mono font-bold tracking-widest py-6 border-b-4 border-[#009900] active:border-b-0 active:translate-y-1 transition-all"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  COMPILING_AGENT...
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4 mr-2 fill-current" />
                  DEPLOY_STRATEGY
                </>
              )}
            </Button>

        </div>
      </div>
    </div>
  );
}