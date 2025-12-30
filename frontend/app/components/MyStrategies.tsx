"use client";

import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { usePrivyWallet } from "@/app/hooks/use-privy-wallet";
import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { Button } from "./ui/button";
import {
  Play,
  Pause,
  Trash2,
  Loader2,
  TrendingUp,
  TrendingDown,
  Terminal,
  Cpu,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Filter,
  Zap,
  Radio,
  Activity,
  Bot,
  Target,
  BarChart3,
  DollarSign,
  Maximize2,
  Crosshair,
  AlertTriangle,
  Layers
} from "lucide-react";
import { 
  getStrategies, 
  getTradingState, 
  getExecutions,
  getTradeStatistics,
  activateStrategy,
  deactivateStrategy,
  deleteStrategy,
  Strategy,
  TradingState,
  Execution,
  TradeStatistics
} from "@/app/lib/api";

type LogFilter = "all" | "buys" | "sells" | "holds";
const LOGS_PER_PAGE = 10;

// --- UTILITY COMPONENTS FOR UI DECORATION ---
const CornerBrackets = ({ className = "" }: { className?: string }) => (
  <>
    <div className={`absolute top-0 left-0 w-2 h-2 border-l border-t border-[#00ff00]/30 ${className}`} />
    <div className={`absolute top-0 right-0 w-2 h-2 border-r border-t border-[#00ff00]/30 ${className}`} />
    <div className={`absolute bottom-0 left-0 w-2 h-2 border-l border-b border-[#00ff00]/30 ${className}`} />
    <div className={`absolute bottom-0 right-0 w-2 h-2 border-r border-b border-[#00ff00]/30 ${className}`} />
  </>
);

const DataCell = ({ label, value, subValue, trend, icon: Icon }: any) => (
  <div className="relative p-3 bg-[#0a0a0a] border border-[#1a1a1a] flex flex-col justify-between group hover:border-[#00ff00]/30 transition-colors">
    <CornerBrackets className="opacity-0 group-hover:opacity-100 transition-opacity" />
    <div className="flex items-center justify-between mb-2">
      <span className="text-[10px] uppercase tracking-wider text-[#006600] font-mono">{label}</span>
      {Icon && <Icon className="h-3 w-3 text-[#004400] group-hover:text-[#00ff00] transition-colors" />}
    </div>
    <div className="font-mono">
      <div className={`text-lg font-bold ${trend === 'up' ? 'text-[#00ff00]' : trend === 'down' ? 'text-[#ff3333]' : 'text-white'}`}>
        {value}
      </div>
      {subValue && <div className="text-[9px] text-[#666] mt-1">{subValue}</div>}
    </div>
  </div>
);

export function MyStrategies() {
  const { authenticated, getAccessToken } = usePrivyWallet();
  const { account } = useWallet();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
  const [tradingState, setTradingState] = useState<TradingState | null>(null);
  const [allExecutions, setAllExecutions] = useState<Map<string, Execution[]>>(new Map());
  const [statistics, setStatistics] = useState<TradeStatistics | null>(null);
  const [loading, setLoading] = useState(true); // Start with true for initial load
  const [loadingExecutions, setLoadingExecutions] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [logFilter, setLogFilter] = useState<LogFilter>("all");
  const [visibleLogCount, setVisibleLogCount] = useState(LOGS_PER_PAGE);
  const feedRef = useRef<HTMLDivElement>(null);
  const cachedTokenRef = useRef<{ token: string | null | undefined; timestamp: number } | null>(null);

  // Get wallet address for API calls
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
      let sessionId = sessionStorage.getItem('aimmm_session_id');
      if (!sessionId) {
        sessionId = `session-${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
        sessionStorage.setItem('aimmm_session_id', sessionId);
      }
      return sessionId;
    }
    
    return undefined;
  };

  // Get cached access token (valid for 30 seconds)
  const getCachedAccessToken = async (): Promise<string | undefined> => {
    if (!authenticated) return undefined;
    
    const now = Date.now();
    // Use cached token if it's less than 30 seconds old
    if (cachedTokenRef.current && (now - cachedTokenRef.current.timestamp) < 30000) {
      console.log("[MyStrategies] Using cached access token");
      return cachedTokenRef.current.token || undefined;
    }
    
    console.log("[MyStrategies] Fetching new access token");
    const token = await getAccessToken();
    cachedTokenRef.current = { token, timestamp: now };
    return token || undefined;
  };

  // Simple loading functions
  const loadStrategies = async () => {
    try {
      setLoading(true);
      console.log("[MyStrategies] Loading strategies...");
      console.log("[MyStrategies] Authenticated:", authenticated);
      
      const token = await getCachedAccessToken();
      const walletAddress = getWalletAddress();
      
      console.log("[MyStrategies] Token available:", !!token);
      console.log("[MyStrategies] Wallet address:", walletAddress);
      
      const data = await getStrategies(token || undefined, { limit: 50 }, walletAddress);
      
      console.log("[MyStrategies] Strategies loaded:", data.strategies.length);
      console.log("[MyStrategies] Strategies data:", data.strategies);
      
      setStrategies(data.strategies);
    } catch (error) {
      console.error("[MyStrategies] Failed to load strategies:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadAllExecutions = async () => {
    setLoadingExecutions(true);
    console.log("[MyStrategies] Loading executions for", strategies.length, "strategies");
    
    const token = await getCachedAccessToken();
    const walletAddress = getWalletAddress();
    
    console.log("[MyStrategies] Executions - Token available:", !!token);
    console.log("[MyStrategies] Executions - Wallet address:", walletAddress);
    
    const execMap = new Map<string, Execution[]>();
    
    for (const strategy of strategies) {
      try {
        console.log(`[MyStrategies] Loading executions for strategy: ${strategy.id} (${strategy.name})`);
        const data = await getExecutions(strategy.id, token || undefined, { limit: 50 }, walletAddress);
        console.log(`[MyStrategies] Executions loaded for ${strategy.name}:`, data.executions.length);
        execMap.set(strategy.id, data.executions);
      } catch (error) {
        console.log(`[MyStrategies] No executions for strategy ${strategy.name} (${strategy.id})`, error);
        execMap.set(strategy.id, []);
      }
    }
    
    console.log("[MyStrategies] All executions loaded. Total strategies with data:", execMap.size);
    setAllExecutions(execMap);
    setLoadingExecutions(false);
  };

  const loadTradingState = async () => {
    if (!selectedStrategyId) {
      console.log("[MyStrategies] loadTradingState: No strategy selected");
      return;
    }
    
    try {
      setLoadingDetails(true);
      console.log(`[MyStrategies] Loading trading state for strategy: ${selectedStrategyId}`);
      
      const token = await getCachedAccessToken();
      const walletAddress = getWalletAddress();
      
      console.log("[MyStrategies] Trading state - Token available:", !!token);
      console.log("[MyStrategies] Trading state - Wallet address:", walletAddress);
      
      const state = await getTradingState(selectedStrategyId, token || undefined, walletAddress);
      
      console.log("[MyStrategies] Trading state loaded successfully:", state);
      setTradingState(state);
    } catch (error) {
      console.error(`[MyStrategies] Failed to load trading state for strategy ${selectedStrategyId}:`, error);
      setTradingState(null);
    } finally {
      setLoadingDetails(false);
    }
  };

  const loadStatistics = async () => {
    if (!selectedStrategyId) {
      console.log("[MyStrategies] loadStatistics: No strategy selected");
      return;
    }
    
    try {
      console.log(`[MyStrategies] Loading statistics for strategy: ${selectedStrategyId}`);
      
      const token = await getCachedAccessToken();
      const walletAddress = getWalletAddress();
      
      console.log("[MyStrategies] Statistics - Token available:", !!token);
      console.log("[MyStrategies] Statistics - Wallet address:", walletAddress);
      
      const data = await getTradeStatistics(selectedStrategyId, token || undefined, walletAddress);
      
      console.log("[MyStrategies] Statistics loaded successfully:", data.statistics);
      setStatistics(data.statistics);
    } catch (error) {
      console.error(`[MyStrategies] Failed to load statistics for strategy ${selectedStrategyId}:`, error);
      setStatistics(null);
    }
  };

  // Action handlers
  const handleActivate = async (strategyId: string, executionInterval?: number) => {
    try {
      const token = await getCachedAccessToken();
      const walletAddress = getWalletAddress();
      const interval = executionInterval || 5;
      await activateStrategy(strategyId, interval, "analysis", token || undefined, walletAddress);
      await loadStrategies();
    } catch (error) {
      console.error("Failed to activate strategy:", error);
      alert("Failed to activate strategy. Please try again.");
    }
  };

  const handleDeactivate = async (strategyId: string) => {
    try {
      const token = await getCachedAccessToken();
      const walletAddress = getWalletAddress();
      await deactivateStrategy(strategyId, token || undefined, walletAddress);
      await loadStrategies();
    } catch (error) {
      console.error("Failed to deactivate strategy:", error);
    }
  };

  const handleDelete = async (strategyId: string) => {
    if (!confirm("Are you sure you want to delete this strategy?")) return;
    try {
      const token = await getCachedAccessToken();
      const walletAddress = getWalletAddress();
      await deleteStrategy(strategyId, token || undefined, walletAddress);
      if (selectedStrategyId === strategyId) {
        setSelectedStrategyId(strategies.length > 1 ? strategies.find(s => s.id !== strategyId)?.id || null : null);
        setTradingState(null);
      }
      await loadStrategies();
    } catch (error) {
      console.error("Failed to delete strategy:", error);
      alert("Failed to delete strategy. Please try again.");
    }
  };

  // Load strategies on mount and when authentication changes
  useEffect(() => {
    console.log("[MyStrategies] useEffect: Auth/wallet changed, loading strategies...");
    console.log("[MyStrategies] - authenticated:", authenticated);
    console.log("[MyStrategies] - account address:", account?.address);
    loadStrategies();
  }, [authenticated, account?.address]);

  // Listen for strategy creation events
  useEffect(() => {
    const handleStrategyCreated = () => {
      console.log("[MyStrategies] Strategy created event received, reloading...");
      loadStrategies();
    };
    
    if (typeof window !== 'undefined') {
      window.addEventListener('strategy-created', handleStrategyCreated);
      return () => window.removeEventListener('strategy-created', handleStrategyCreated);
    }
  }, []);

  // Load executions when strategies change
  useEffect(() => {
    console.log("[MyStrategies] useEffect: Strategies changed");
    console.log("[MyStrategies] - strategies.length:", strategies.length);
    console.log("[MyStrategies] - selectedStrategyId:", selectedStrategyId);
    
    if (strategies.length > 0) {
      // Small delay to avoid rate limiting
      setTimeout(() => {
        loadAllExecutions();
      }, 100);
      
      if (!selectedStrategyId) {
        console.log("[MyStrategies] Auto-selecting first strategy:", strategies[0].id);
        setSelectedStrategyId(strategies[0].id);
      }
    }
  }, [strategies]);

  // Load trading state and statistics when strategy selection changes
  useEffect(() => {
    console.log("[MyStrategies] useEffect: Strategy selection changed");
    console.log("[MyStrategies] - selectedStrategyId:", selectedStrategyId);
    
    if (selectedStrategyId) {
      console.log("[MyStrategies] Loading trading state and statistics...");
      // Small delay to avoid rate limiting
      setTimeout(() => {
        loadTradingState();
      }, 150);
      setTimeout(() => {
        loadStatistics();
      }, 300);
    }
  }, [selectedStrategyId]);

  const selectedStrategy = useMemo(() => strategies.find(s => s.id === selectedStrategyId) || null, [strategies, selectedStrategyId]);

  const combinedExecutions = useMemo(() => {
    const all: (Execution & { strategyName: string; strategyId: string })[] = [];
    allExecutions.forEach((execs, strategyId) => {
      const strategy = strategies.find(s => s.id === strategyId);
      execs.forEach(exec => {
        all.push({ ...exec, strategyName: strategy?.name || "Unknown", strategyId });
      });
    });
    all.sort((a, b) => new Date(b.execution_timestamp).getTime() - new Date(a.execution_timestamp).getTime());
    if (logFilter === "all") return all;
    return all.filter(e => {
      if (logFilter === "buys") return e.decision === "BUY";
      if (logFilter === "sells") return e.decision === "SELL";
      if (logFilter === "holds") return e.decision === "HOLD";
      return true;
    });
  }, [allExecutions, strategies, logFilter]);

  const visibleLogs = useMemo(() => combinedExecutions.slice(0, visibleLogCount), [combinedExecutions, visibleLogCount]);
  const hasMoreLogs = visibleLogCount < combinedExecutions.length;
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    if (scrollHeight - scrollTop - clientHeight < 100 && hasMoreLogs) {
      setVisibleLogCount(prev => Math.min(prev + LOGS_PER_PAGE, combinedExecutions.length));
    }
  }, [hasMoreLogs, combinedExecutions.length]);

  const formatTime = (timestamp: string) => new Date(timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  const getModelName = (provider: string | undefined) => {
    if (!provider) return "DeepSeek R1";
    const parts = provider.split("/");
    return parts[parts.length - 1].replace(/-/g, " ").replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div className="space-y-4">
      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* 1. STRATEGY SELECTOR (TABS STYLE) & ACTIONS */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      {loading ? (
        // Loading state
        <div className="flex items-center justify-center border border-[#1a1a1a] bg-[#050505] p-12">
          <Loader2 className="h-8 w-8 text-[#00ff00] animate-spin" />
          <span className="ml-3 text-sm font-mono text-[#00ff00]">Loading strategies...</span>
        </div>
      ) : strategies.length === 0 ? (
        // Empty state - no strategies yet
        <div className="flex flex-col items-center justify-center border border-[#1a1a1a] bg-[#050505] p-12">
          <div className="w-16 h-16 bg-[#00ff00]/10 rounded-full flex items-center justify-center mb-4 border border-[#00ff00]/30">
            <Target className="h-8 w-8 text-[#00ff00]" />
          </div>
          <h3 className="text-lg font-mono text-white mb-2">No Strategies Yet</h3>
          <p className="text-sm text-[#666] font-mono mb-6 text-center max-w-md">
            Create your first autonomous trading strategy to get started. Go to Strategy Builder to initialize a new agent.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-0 border border-[#1a1a1a] bg-[#050505]">
          {/* Tab Bar */}
          <div className="flex items-center overflow-x-auto border-b border-[#1a1a1a] bg-[#0a0a0a] scrollbar-hide">
             {strategies.map((strategy) => (
              <button
                key={strategy.id}
                onClick={() => setSelectedStrategyId(strategy.id)}
                className={`relative flex items-center gap-2 px-4 py-3 text-xs font-mono transition-all whitespace-nowrap border-r border-[#1a1a1a] ${
                  selectedStrategyId === strategy.id
                    ? 'bg-[#111] text-[#00ff00]'
                    : 'text-[#666] hover:text-[#00ff00] hover:bg-[#0f0f0f]'
                }`}
              >
                {selectedStrategyId === strategy.id && (
                  <div className="absolute top-0 left-0 right-0 h-[2px] bg-[#00ff00] shadow-[0_0_10px_#00ff00]" />
                )}
                <div className={`w-1.5 h-1.5 rounded-full ${
                  strategy.is_active ? 'bg-[#00ff00] animate-pulse' : 'bg-[#333]'
                }`} />
                {strategy.name}
              </button>
            ))}
          </div>

          {/* Selected Strategy Control Bar */}
          {selectedStrategy && (
            <div className="p-3 flex flex-wrap items-center justify-between gap-4 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-100">
              <div className="flex items-center gap-4">
                <div className="flex flex-col">
                  <span className="text-[9px] text-[#006600] font-mono mb-0.5">ACTIVE MODEL</span>
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-[#0a0a0a] border border-[#1a1a1a] rounded-sm">
                     <Cpu className="h-3 w-3 text-[#00ff00]" />
                     <span className="text-xs font-mono text-[#00ff00]">
                      {getModelName(selectedStrategy.strategy_config?.llm_provider)}
                     </span>
                  </div>
                </div>

                <div className="h-8 w-px bg-[#1a1a1a]" />

                <div className="flex items-center gap-3">
                   <div className="flex flex-col">
                      <span className="text-[9px] text-[#006600] font-mono">INTERVAL</span>
                      <span className="text-xs font-mono text-white">{selectedStrategy.execution_interval || 5}m</span>
                   </div>
                   <div className="flex flex-col">
                      <span className="text-[9px] text-[#006600] font-mono">MODE</span>
                      <span className="text-xs font-mono text-white">
                        {selectedStrategy.strategy_config?.paper_trading_config?.trading_mode === "real" ? "LIVE" : "PAPER"}
                      </span>
                   </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                 {selectedStrategy.is_active ? (
                    <Button onClick={() => handleDeactivate(selectedStrategy.id)} size="sm" 
                      className="h-8 bg-[#1a0505] text-[#ff3333] border border-[#ff3333]/50 hover:bg-[#ff3333]/10 font-mono text-xs tracking-wider">
                      <Pause className="h-3 w-3 mr-2" /> HALT_SYSTEM
                    </Button>
                  ) : (
                    <Button onClick={() => handleActivate(selectedStrategy.id, selectedStrategy.execution_interval)} size="sm" 
                      className="h-8 bg-[#002200] text-[#00ff00] border border-[#00ff00]/50 hover:bg-[#00ff00]/10 font-mono text-xs tracking-wider">
                      <Play className="h-3 w-3 mr-2" /> INITIALIZE
                    </Button>
                  )}
                  <Button onClick={() => handleDelete(selectedStrategy.id)} size="sm" variant="ghost" className="h-8 w-8 p-0 text-[#666] hover:text-[#ff3333]">
                    <Trash2 className="h-4 w-4" />
                  </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* 2. LIVE TICKER (GLOBAL STATS) */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      {!loading && strategies.length > 0 && (
        loadingDetails ? (
          <div className="flex items-center justify-center border border-[#1a1a1a] bg-[#0a0a0a] p-8">
            <Loader2 className="h-6 w-6 text-[#00ff00] animate-spin mr-3" />
            <span className="text-sm font-mono text-[#00ff00]">Loading trading state...</span>
          </div>
        ) : tradingState ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-0 border border-[#1a1a1a] bg-[#0a0a0a] overflow-hidden">
            <div className="p-3 border-r border-[#1a1a1a] relative group">
               <div className="absolute top-0 left-0 w-1 h-full bg-[#00ff00] opacity-50" />
               <div className="text-[9px] text-[#006600] font-mono mb-1 uppercase">Total Equity</div>
               <div className="text-xl font-bold font-mono text-white flex items-baseline gap-1">
                  ${tradingState.total_portfolio_value.toFixed(2)}
               </div>
            </div>
            
            <div className="p-3 border-r border-[#1a1a1a]">
               <div className="text-[9px] text-[#006600] font-mono mb-1 uppercase">Unrealized P&L</div>
               <div className={`text-xl font-bold font-mono flex items-center gap-2 ${tradingState.unrealized_pnl >= 0 ? 'text-[#00ff00]' : 'text-[#ff3333]'}`}>
                  {tradingState.unrealized_pnl >= 0 ? '+' : ''}${tradingState.unrealized_pnl.toFixed(2)}
                  <span className="text-xs opacity-70 bg-black/30 px-1 py-0.5 rounded">
                     {tradingState.unrealized_pnl_pct.toFixed(2)}%
                  </span>
               </div>
            </div>

            <div className="p-3 border-r border-[#1a1a1a]">
               <div className="text-[9px] text-[#006600] font-mono mb-1 uppercase">Active Positions</div>
               <div className="text-xl font-bold font-mono text-white">
                  {tradingState.active_positions} <span className="text-xs text-[#666] font-normal">OPEN</span>
               </div>
            </div>

            <div className="p-3 flex items-center justify-end pr-6 bg-[#0d0d0d]">
               <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#00ff00] animate-pulse shadow-[0_0_8px_#00ff00]" />
                  <span className="text-xs font-mono text-[#00ff00] tracking-widest">SYSTEM ONLINE</span>
               </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center border border-[#1a1a1a] border-dashed bg-[#050505] p-6">
            <AlertTriangle className="h-5 w-5 text-[#666] mr-2" />
            <span className="text-xs font-mono text-[#666]">Initialize strategy to view trading state</span>
          </div>
        )
      )}

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* 3. MAIN DASHBOARD GRID */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      {!loading && strategies.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        
        {/* LEFT: EXECUTION LOGS (Terminal Style) - Spans 7 cols */}
        <div className="lg:col-span-7 flex flex-col h-[500px] border border-[#1a1a1a] bg-[#050505] relative overflow-hidden">
          {/* Scanlines Effect */}
          <div className="absolute inset-0 pointer-events-none z-10 opacity-[0.03] bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,#00ff00_2px,#00ff00_4px)]" />
          
          {/* Terminal Header */}
          <div className="flex items-center justify-between px-3 py-2 bg-[#111] border-b border-[#1a1a1a] z-20">
            <div className="flex items-center gap-2">
              <Terminal className="h-4 w-4 text-[#00ff00]" />
              <span className="text-xs font-mono text-[#00ff00] font-bold tracking-wider">
                EXECUTION_FEED<span className="animate-pulse">_</span>
              </span>
            </div>
            <div className="flex gap-1">
               {(["all", "buys", "sells", "holds"] as LogFilter[]).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => { setLogFilter(filter); setVisibleLogCount(LOGS_PER_PAGE); }}
                    className={`px-2 py-0.5 text-[9px] font-mono uppercase border ${
                      logFilter === filter ? 'border-[#00ff00] text-[#00ff00] bg-[#00ff00]/10' : 'border-transparent text-[#666] hover:text-white'
                    }`}
                  >
                    {filter}
                  </button>
               ))}
            </div>
          </div>

          {/* Logs Container */}
          <div 
            ref={feedRef}
            onScroll={handleScroll}
            className="flex-1 overflow-y-auto p-2 space-y-1 relative z-20 font-mono text-xs"
          >
             {loadingExecutions ? (
                <div className="h-full flex flex-col items-center justify-center text-[#006600]">
                   <Loader2 className="h-6 w-6 animate-spin mb-2" />
                   <span>DECRYPTING DATA STREAMS...</span>
                </div>
             ) : combinedExecutions.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center opacity-30">
                   <Target className="h-12 w-12 text-[#00ff00] mb-2" />
                   <span className="text-[#00ff00]">NO SIGNALS DETECTED</span>
                </div>
             ) : (
                visibleLogs.map((execution, i) => (
                   <div key={execution.id} className="group relative pl-3 py-2 border-l-2 border-[#1a1a1a] hover:border-[#00ff00] hover:bg-[#00ff00]/5 transition-all">
                      <div className="flex items-center justify-between mb-1">
                         <div className="flex items-center gap-2">
                            <span className="text-[#666] text-[10px]">{formatTime(execution.execution_timestamp)}</span>
                            <span className={`px-1.5 py-0.5 text-[9px] font-bold border ${
                               execution.decision === "BUY" ? "text-[#00ff00] border-[#00ff00] bg-[#00ff00]/10" :
                               execution.decision === "SELL" ? "text-[#ff3333] border-[#ff3333] bg-[#ff3333]/10" :
                               "text-[#888] border-[#333]"
                            }`}>
                               {execution.decision}
                            </span>
                            <span className="text-[#00ff00] opacity-70">[{execution.strategyName}]</span>
                         </div>
                         <div className="text-[10px] text-[#444] group-hover:text-[#00ff00]">
                            CFD: {(execution.confidence * 100).toFixed(0)}%
                         </div>
                      </div>
                      
                      {execution.reasoning && (
                         <div className="text-[#aaa] leading-relaxed opacity-80 pl-2 border-l border-[#333] ml-1">
                            {execution.reasoning}
                         </div>
                      )}

                      {execution.trade_executed && execution.price && (
                         <div className="mt-1 ml-1 flex items-center gap-2 text-[10px] bg-[#111] w-fit px-2 py-0.5 border border-[#333]">
                            <Zap className="h-3 w-3 text-[#ffff00]" />
                            <span className="text-[#ccc]">FILLED @</span>
                            <span className="text-[#ffff00]">${execution.price?.toFixed(4)}</span>
                         </div>
                      )}
                   </div>
                ))
             )}
             {hasMoreLogs && <div className="text-center py-2 text-[#666] text-[10px] animate-pulse">-- SCROLL FOR HISTORY --</div>}
          </div>
        </div>

        {/* RIGHT: ANALYTICS ENGINE (Creative Stats) - Spans 5 cols */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          
          {/* A. PERFORMANCE GRID */}
          {loadingDetails ? (
            <div className="bg-[#050505] border border-[#1a1a1a] p-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 text-[#00ff00] animate-spin mr-3" />
              <span className="text-sm font-mono text-[#00ff00]">Loading analytics...</span>
            </div>
          ) : statistics ? (
            <div className="bg-[#050505] border border-[#1a1a1a] p-1">
               <div className="flex items-center gap-2 px-2 py-1 mb-1 border-b border-[#1a1a1a]/50">
                  <BarChart3 className="h-3 w-3 text-[#00ff00]" />
                  <span className="text-[10px] font-mono text-[#00ff00]">ANALYTICS_CORE</span>
               </div>
               
               <div className="grid grid-cols-2 gap-1">
                  {/* Win Rate Gauge Cell */}
                  <div className="row-span-2 bg-[#080808] border border-[#1a1a1a] p-4 flex flex-col items-center justify-center relative overflow-hidden group">
                     <CornerBrackets />
                     <div className="relative w-24 h-24 flex items-center justify-center">
                        <svg className="transform -rotate-90 w-full h-full">
                           <circle cx="48" cy="48" r="40" stroke="#1a1a1a" strokeWidth="8" fill="transparent" />
                           <circle cx="48" cy="48" r="40" stroke={statistics.win_rate >= 50 ? "#00ff00" : "#ff3333"} strokeWidth="8" fill="transparent" 
                                   strokeDasharray={251.2} strokeDashoffset={251.2 * (1 - statistics.win_rate / 100)} className="transition-all duration-1000 ease-out" />
                        </svg>
                        <div className="absolute text-center">
                           <div className="text-xl font-bold font-mono text-white">{statistics.win_rate.toFixed(1)}%</div>
                           <div className="text-[9px] text-[#666] font-mono">WIN RATE</div>
                        </div>
                     </div>
                  </div>

                  {/* Net P&L Cell */}
                  <DataCell 
                     label="NET P&L" 
                     value={`${statistics.net_pnl >= 0 ? '+' : ''}$${statistics.net_pnl.toFixed(2)}`}
                     trend={statistics.net_pnl >= 0 ? 'up' : 'down'}
                     icon={DollarSign}
                  />

                  {/* Profit Factor */}
                  <DataCell 
                     label="PROFIT FACTOR" 
                     value={statistics.profit_factor?.toFixed(2) || "0.00"}
                     trend={(statistics.profit_factor || 0) > 1.5 ? 'up' : 'neutral'}
                     icon={TrendingUp}
                  />

                  {/* Risk Metrics */}
                  <DataCell 
                     label="SHARPE" 
                     value={statistics.sharpe_ratio?.toFixed(2) || "0.00"}
                     icon={Activity}
                  />

                   <DataCell 
                     label="MAX DRAWDOWN" 
                     value={`-${statistics.max_drawdown_pct?.toFixed(2)}%`}
                     trend="down"
                     icon={AlertTriangle}
                  />
                  
                  {/* Trade Counts */}
                   <div className="col-span-2 bg-[#080808] border border-[#1a1a1a] p-2 flex justify-between items-center font-mono text-xs">
                      <div className="flex gap-4">
                         <span className="text-[#666]">TRADES: <span className="text-white">{statistics.total_trades}</span></span>
                         <span className="text-[#666]">W: <span className="text-[#00ff00]">{statistics.winning_trades}</span></span>
                         <span className="text-[#666]">L: <span className="text-[#ff3333]">{statistics.losing_trades}</span></span>
                      </div>
                      <div className="text-[10px] text-[#006600]">AVG: ${statistics.expectancy?.toFixed(2)}</div>
                   </div>
               </div>
            </div>
          ) : (
            <div className="h-full border border-[#1a1a1a] border-dashed flex flex-col items-center justify-center p-8 bg-[#050505]">
               <Crosshair className="h-8 w-8 text-[#004400] mb-2" />
               <span className="text-xs font-mono text-[#006600] text-center">
                  NO ANALYTICS DATA YET<br/>ACTIVATE STRATEGY TO BEGIN
               </span>
            </div>
          )}

          {/* B. ACTIVE POSITIONS (Compact List) */}
          {loadingDetails ? (
            <div className="bg-[#050505] border border-[#1a1a1a] p-8 flex items-center justify-center">
              <Loader2 className="h-6 w-6 text-[#00ff00] animate-spin" />
            </div>
          ) : tradingState && tradingState.balances && tradingState.balances.filter(b => b.token_symbol !== "USDC" && b.balance > 0).length > 0 ? (
            <div className="bg-[#050505] border border-[#1a1a1a] flex-1 flex flex-col">
               <div className="flex items-center gap-2 px-3 py-2 border-b border-[#1a1a1a] bg-[#111]">
                  <Layers className="h-3 w-3 text-[#00ff00]" />
                  <span className="text-[10px] font-mono text-[#00ff00]">ACTIVE_ASSETS</span>
               </div>
               <div className="p-2 space-y-1 overflow-y-auto max-h-[200px]">
                  {tradingState.balances
                     .filter(b => b.token_symbol !== "USDC" && b.balance > 0)
                     .map((balance, idx) => (
                     <div key={idx} className="flex justify-between items-center p-2 bg-[#0a0a0a] border border-[#1a1a1a] hover:border-[#00ff00]/30 transition-colors">
                        <div className="flex items-center gap-3">
                           <div className="w-1 h-8 bg-[#00ff00]/50" />
                           <div>
                              <div className="text-xs font-bold font-mono text-white">{balance.token_symbol}</div>
                              <div className="text-[9px] text-[#666] font-mono">{balance.balance.toFixed(4)} UNITS</div>
                           </div>
                        </div>
                        <div className="text-right">
                           <div className="text-xs font-mono text-white">${balance.usd_value.toFixed(2)}</div>
                           <div className={`text-[9px] font-mono ${(balance.unrealized_pnl || 0) >= 0 ? 'text-[#00ff00]' : 'text-[#ff3333]'}`}>
                              {(balance.unrealized_pnl || 0) >= 0 ? '+' : ''}${(balance.unrealized_pnl || 0).toFixed(2)}
                           </div>
                        </div>
                     </div>
                  ))}
               </div>
            </div>
          ) : (
            <div className="h-full border border-[#1a1a1a] border-dashed flex flex-col items-center justify-center p-8 bg-[#050505]">
               <Layers className="h-8 w-8 text-[#004400] mb-2" />
               <span className="text-xs font-mono text-[#006600] text-center">
                  NO ACTIVE POSITIONS
               </span>
            </div>
          )}
        </div>
      </div>
      )}
    </div>
  );
}