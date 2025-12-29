"use client";

import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { usePrivyWallet } from "@/app/hooks/use-privy-wallet";
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
  RefreshCw,
  Filter,
  ChevronDown,
  ChevronUp,
  Zap,
  Clock,
  Radio,
  Activity,
  Bot,
  Target,
  BarChart3,
  DollarSign,
  Percent,
  Timer
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

export function MyStrategies() {
  const { authenticated, getAccessToken } = usePrivyWallet();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
  const [tradingState, setTradingState] = useState<TradingState | null>(null);
  const [allExecutions, setAllExecutions] = useState<Map<string, Execution[]>>(new Map());
  const [statistics, setStatistics] = useState<TradeStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [logFilter, setLogFilter] = useState<LogFilter>("all");
  const [visibleLogCount, setVisibleLogCount] = useState(LOGS_PER_PAGE);
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadStrategies();
  }, [authenticated]);

  useEffect(() => {
    if (strategies.length > 0) {
      loadAllExecutions();
      if (!selectedStrategyId && strategies.length > 0) {
        setSelectedStrategyId(strategies[0].id);
      }
    }
  }, [strategies]);

  useEffect(() => {
    if (selectedStrategyId) {
      loadTradingState();
      loadStatistics();
    }
  }, [selectedStrategyId]);

  const loadStrategies = async () => {
    try {
      setLoading(true);
      const token = authenticated ? await getAccessToken() : undefined;
      const data = await getStrategies(token || undefined, { limit: 50 });
      setStrategies(data.strategies);
    } catch (error) {
      console.error("Failed to load strategies:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadAllExecutions = async () => {
    const token = authenticated ? await getAccessToken() : undefined;
    const execMap = new Map<string, Execution[]>();
    
    for (const strategy of strategies) {
      try {
        const data = await getExecutions(strategy.id, token || undefined, { limit: 50 });
        execMap.set(strategy.id, data.executions);
      } catch (error) {
        console.error(`Failed to load executions for ${strategy.id}:`, error);
      }
    }
    setAllExecutions(execMap);
  };

  const loadTradingState = async () => {
    if (!selectedStrategyId) return;
    try {
      const token = authenticated ? await getAccessToken() : undefined;
      const state = await getTradingState(selectedStrategyId, token || undefined);
      setTradingState(state);
    } catch (error) {
      console.error("Failed to load trading state:", error);
    }
  };

  const loadStatistics = async () => {
    if (!selectedStrategyId) return;
    try {
      const token = authenticated ? await getAccessToken() : undefined;
      const data = await getTradeStatistics(selectedStrategyId, token || undefined);
      setStatistics(data.statistics);
    } catch (error) {
      console.error("Failed to load statistics:", error);
      setStatistics(null);
    }
  };

  const handleActivate = async (strategyId: string, executionInterval?: number) => {
    try {
      const token = authenticated ? await getAccessToken() : undefined;
      const interval = executionInterval || 5;
      await activateStrategy(strategyId, interval, "analysis", token || undefined);
      await loadStrategies();
    } catch (error) {
      console.error("Failed to activate strategy:", error);
      alert("Failed to activate strategy. Please try again.");
    }
  };

  const handleDeactivate = async (strategyId: string) => {
    try {
      const token = authenticated ? await getAccessToken() : undefined;
      await deactivateStrategy(strategyId, token || undefined);
      await loadStrategies();
    } catch (error) {
      console.error("Failed to deactivate strategy:", error);
    }
  };

  const handleDelete = async (strategyId: string) => {
    if (!confirm("Are you sure you want to delete this strategy?")) return;
    try {
      const token = authenticated ? await getAccessToken() : undefined;
      await deleteStrategy(strategyId, token || undefined);
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

  const selectedStrategy = useMemo(() => 
    strategies.find(s => s.id === selectedStrategyId) || null
  , [strategies, selectedStrategyId]);

  const combinedExecutions = useMemo(() => {
    const all: (Execution & { strategyName: string; strategyId: string })[] = [];
    
    allExecutions.forEach((execs, strategyId) => {
      const strategy = strategies.find(s => s.id === strategyId);
      execs.forEach(exec => {
        all.push({
          ...exec,
          strategyName: strategy?.name || "Unknown",
          strategyId
        });
      });
    });

    all.sort((a, b) => 
      new Date(b.execution_timestamp).getTime() - new Date(a.execution_timestamp).getTime()
    );

    if (logFilter === "all") return all;
    return all.filter(e => {
      if (logFilter === "buys") return e.decision === "BUY";
      if (logFilter === "sells") return e.decision === "SELL";
      if (logFilter === "holds") return e.decision === "HOLD";
      return true;
    });
  }, [allExecutions, strategies, logFilter]);

  const visibleLogs = useMemo(() => 
    combinedExecutions.slice(0, visibleLogCount)
  , [combinedExecutions, visibleLogCount]);

  const hasMoreLogs = visibleLogCount < combinedExecutions.length;

  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    if (scrollHeight - scrollTop - clientHeight < 100 && hasMoreLogs) {
      setVisibleLogCount(prev => Math.min(prev + LOGS_PER_PAGE, combinedExecutions.length));
    }
  }, [hasMoreLogs, combinedExecutions.length]);

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case "BUY": return "text-[#00ff00]";
      case "SELL": return "text-[#ff3333]";
      default: return "text-[#666]";
    }
  };

  const getDecisionBg = (decision: string) => {
    switch (decision) {
      case "BUY": return "bg-[#00ff00]/10 border-[#00ff00]/30";
      case "SELL": return "bg-[#ff3333]/10 border-[#ff3333]/30";
      default: return "bg-[#333]/10 border-[#333]/30";
    }
  };

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case "BUY": return <ArrowUpRight className="h-3 w-3" />;
      case "SELL": return <ArrowDownRight className="h-3 w-3" />;
      default: return <Minus className="h-3 w-3" />;
    }
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit',
      hour12: false 
    });
  };

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const getModelName = (provider: string | undefined) => {
    if (!provider) return "DeepSeek R1";
    const parts = provider.split("/");
    return parts[parts.length - 1].replace(/-/g, " ").replace(/\b\w/g, l => l.toUpperCase());
  };

  return (
    <div className="space-y-4">
      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* STRATEGY DOCK - TOP */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      <div className="bg-[#0a0a0a] border border-[#1a1a1a]">
        {/* Strategy Selector Tabs */}
        <div className="flex items-center gap-1 px-4 py-2 border-b border-[#1a1a1a] overflow-x-auto">
          {strategies.length === 0 ? (
            <div className="text-xs text-[#006600] font-mono py-2">
              No strategies. Create one in ./strategies
            </div>
          ) : (
            strategies.map((strategy) => (
              <button
                key={strategy.id}
                onClick={() => setSelectedStrategyId(strategy.id)}
                className={`flex items-center gap-2 px-3 py-2 text-xs font-mono transition-all whitespace-nowrap ${
                  selectedStrategyId === strategy.id
                    ? 'bg-[#00ff00]/10 text-[#00ff00] border border-[#00ff00]'
                    : 'text-[#666] hover:text-[#00ff00] border border-transparent hover:border-[#00ff00]/30'
                }`}
              >
                <div className={`w-2 h-2 rounded-full ${
                  strategy.is_active 
                    ? 'bg-[#00ff00] shadow-[0_0_6px_rgba(0,255,0,0.5)] animate-pulse' 
                    : 'bg-[#333]'
                }`} />
                {strategy.name}
              </button>
            ))
          )}
          <Button
            onClick={() => { loadStrategies(); loadAllExecutions(); }}
            size="sm"
            variant="ghost"
            className="ml-auto h-7 text-[#006600] hover:text-[#00ff00] hover:bg-[#00ff00]/10"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Selected Strategy Info */}
        {selectedStrategy && (
          <div className="p-4">
            <div className="flex items-start justify-between gap-4">
              {/* Strategy Details */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3 mb-2">
                  <div className="flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-[#00ff00]" />
                    <h2 className="text-lg font-mono font-bold text-[#00ff00]">
                      {selectedStrategy.name}
                    </h2>
                  </div>
                  {selectedStrategy.is_active && (
                    <div className="flex items-center gap-1 px-2 py-0.5 bg-[#00ff00]/20 border border-[#00ff00]">
                      <Radio className="h-3 w-3 text-[#00ff00] animate-pulse" />
                      <span className="text-[10px] font-mono text-[#00ff00]">RUNNING</span>
                    </div>
                  )}
                </div>
                
                {selectedStrategy.description && (
                  <p className="text-xs text-[#006600] font-mono mb-3 line-clamp-2">
                    {selectedStrategy.description}
                  </p>
                )}

                {/* Strategy Meta */}
                <div className="flex items-center gap-4 flex-wrap">
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-[#111] border border-[#1a1a1a]">
                    <Bot className="h-3 w-3 text-[#00ff00]" />
                    <span className="text-[10px] font-mono text-[#006600]">MODEL:</span>
                    <span className="text-[10px] font-mono text-[#00ff00]">
                      {getModelName(selectedStrategy.strategy_config?.llm_provider)}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-[#111] border border-[#1a1a1a]">
                    <Timer className="h-3 w-3 text-[#00ff00]" />
                    <span className="text-[10px] font-mono text-[#006600]">INTERVAL:</span>
                    <span className="text-[10px] font-mono text-[#00ff00]">
                      {selectedStrategy.execution_interval || 5} min
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-[#111] border border-[#1a1a1a]">
                    <Target className="h-3 w-3 text-[#00ff00]" />
                    <span className="text-[10px] font-mono text-[#006600]">MODE:</span>
                    <span className="text-[10px] font-mono text-[#00ff00]">
                      {selectedStrategy.strategy_config?.paper_trading_config?.trading_mode === "real" ? "LIVE" : "PAPER"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {selectedStrategy.is_active ? (
                  <Button
                    onClick={() => handleDeactivate(selectedStrategy.id)}
                    size="sm"
                    className="h-9 px-4 bg-transparent text-[#ff3333] hover:bg-[#ff3333]/20 border border-[#ff3333] font-mono text-xs"
                  >
                    <Pause className="h-4 w-4 mr-2" />
                    PAUSE
                  </Button>
                ) : (
                  <Button
                    onClick={() => handleActivate(selectedStrategy.id, selectedStrategy.execution_interval)}
                    size="sm"
                    className="h-9 px-4 bg-[#00ff00] text-black hover:bg-[#00cc00] font-mono text-xs"
                  >
                    <Play className="h-4 w-4 mr-2" />
                    START
                  </Button>
                )}
                <Button
                  onClick={() => handleDelete(selectedStrategy.id)}
                  size="sm"
                  variant="ghost"
                  className="h-9 w-9 p-0 text-[#ff3333] hover:bg-[#ff3333]/20"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* MAIN CONTENT: 2/3 Terminal + 1/3 Metrics */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* LEFT: Execution Terminal (2/3) */}
        <div className="lg:col-span-2 flex flex-col">
          <div className="flex-1 min-h-0 flex flex-col bg-[#0d0d0d] border border-[#1a1a1a]">
            {/* Terminal Chrome */}
            <div className="flex items-center justify-between px-4 py-2 bg-[#111] border-b border-[#1a1a1a]">
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-[#ff5f56]" />
                  <div className="w-3 h-3 rounded-full bg-[#ffbd2e]" />
                  <div className="w-3 h-3 rounded-full bg-[#27ca40]" />
                </div>
                <div className="flex items-center gap-2">
                  <Terminal className="h-4 w-4 text-[#00ff00]" />
                  <span className="text-sm font-mono text-[#00ff00] font-bold">
                    EXECUTION_FEED
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2 text-[10px] font-mono text-[#006600]">
                <span>Showing {visibleLogs.length} of {combinedExecutions.length}</span>
              </div>
            </div>

            {/* Filter Bar */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-[#1a1a1a]">
              <div className="flex items-center gap-1">
                <Filter className="h-3 w-3 text-[#006600] mr-2" />
                {(["all", "buys", "sells", "holds"] as LogFilter[]).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => { setLogFilter(filter); setVisibleLogCount(LOGS_PER_PAGE); }}
                    className={`px-3 py-1 text-[10px] font-mono uppercase transition-all ${
                      logFilter === filter
                        ? filter === "buys" 
                          ? "bg-[#00ff00]/20 text-[#00ff00] border border-[#00ff00]"
                          : filter === "sells"
                          ? "bg-[#ff3333]/20 text-[#ff3333] border border-[#ff3333]"
                          : "bg-[#00ff00]/20 text-[#00ff00] border border-[#00ff00]"
                        : "text-[#666] hover:text-[#00ff00] border border-transparent"
                    }`}
                  >
                    [{filter}]
                  </button>
                ))}
              </div>
            </div>

            {/* Feed Content with Lazy Loading */}
            <div 
              ref={feedRef}
              onScroll={handleScroll}
              className="flex-1 bg-[#080808] overflow-y-auto relative"
              style={{ maxHeight: '450px' }}
            >
              {/* Scanline Effect */}
              <div className="absolute inset-0 pointer-events-none opacity-[0.02] bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,255,0,0.03)_2px,rgba(0,255,0,0.03)_4px)]" />
              
              {loading && combinedExecutions.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64">
                  <Loader2 className="h-8 w-8 text-[#00ff00] animate-spin mb-4" />
                  <p className="text-[#006600] font-mono text-sm">Initializing feed...</p>
                </div>
              ) : combinedExecutions.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 p-8">
                  <Terminal className="h-12 w-12 text-[#006600] opacity-30 mb-4" />
                  <p className="text-[#006600] font-mono text-sm mb-2">No execution logs yet</p>
                  <p className="text-[#004400] font-mono text-xs">
                    Start a strategy to see real-time trading decisions
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-[#1a1a1a]/50">
                  {visibleLogs.map((execution, index) => (
                    <div
                      key={execution.id}
                      className="group relative hover:bg-[#0f0f0f] transition-all duration-150"
                    >
                      {index === 0 && (
                        <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-[#00ff00] animate-pulse" />
                      )}
                      
                      <div className="px-4 py-3">
                        <div className="flex items-start gap-3 flex-wrap">
                          {/* Timestamp */}
                          <div className="flex-shrink-0 w-16 text-right">
                            <div className="text-[10px] font-mono text-[#006600]">
                              {formatTime(execution.execution_timestamp)}
                            </div>
                            <div className="text-[9px] font-mono text-[#004400]">
                              {formatDate(execution.execution_timestamp)}
                            </div>
                          </div>

                          {/* Decision Badge */}
                          <div className={`flex-shrink-0 flex items-center gap-1 px-2 py-1 border ${getDecisionBg(execution.decision)}`}>
                            <span className={getDecisionColor(execution.decision)}>
                              {getDecisionIcon(execution.decision)}
                            </span>
                            <span className={`text-[10px] font-mono font-bold ${getDecisionColor(execution.decision)}`}>
                              {execution.decision}
                            </span>
                          </div>

                          {/* Strategy Tag */}
                          <div className="flex-shrink-0 px-2 py-1 bg-[#1a1a1a] border border-[#333]">
                            <span className="text-[10px] font-mono text-[#00ff00]">
                              {execution.strategyName}
                            </span>
                          </div>

                          {/* Confidence */}
                          <div className="flex items-center gap-2">
                            <div className="w-12 h-1.5 bg-[#1a1a1a] overflow-hidden">
                              <div 
                                className={`h-full transition-all ${
                                  execution.confidence >= 0.7 ? 'bg-[#00ff00]' :
                                  execution.confidence >= 0.4 ? 'bg-[#ffff00]' : 'bg-[#ff3333]'
                                }`}
                                style={{ width: `${execution.confidence * 100}%` }}
                              />
                            </div>
                            <span className="text-[9px] font-mono text-[#006600]">
                              {(execution.confidence * 100).toFixed(0)}%
                            </span>
                          </div>

                          {execution.trade_executed && (
                            <div className="flex items-center gap-1 px-2 py-0.5 bg-[#00ff00]/10 border border-[#00ff00]/30">
                              <Zap className="h-2.5 w-2.5 text-[#00ff00]" />
                              <span className="text-[9px] font-mono text-[#00ff00]">EXECUTED</span>
                            </div>
                          )}
                        </div>

                        {execution.reasoning && (
                          <div className="mt-2 ml-[76px] text-xs font-mono text-[#006600] leading-relaxed">
                            <span className="text-[#00ff00] mr-2">&gt;</span>
                            {execution.reasoning}
                          </div>
                        )}

                        {execution.trade_executed && execution.price && (
                          <div className="mt-2 ml-[76px] flex items-center gap-3 text-[10px] font-mono">
                            <span className="text-[#006600]">IN:</span>
                            <span className="text-[#00ff00]">
                              {execution.side === "buy" 
                                ? `$${execution.amount_in?.toFixed(2)}` 
                                : `${execution.amount_in?.toFixed(4)}`}
                            </span>
                            <span className="text-[#333]">→</span>
                            <span className="text-[#006600]">OUT:</span>
                            <span className="text-[#00ff00]">
                              {execution.side === "buy" 
                                ? `${execution.amount_out?.toFixed(4)}`
                                : `$${execution.amount_out?.toFixed(2)}`}
                            </span>
                            <span className="text-[#333]">@</span>
                            <span className="text-[#00ff00]">${execution.price?.toFixed(4)}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Load More Indicator */}
                  {hasMoreLogs && (
                    <div className="p-4 text-center">
                      <div className="text-[10px] font-mono text-[#006600]">
                        Scroll for more... ({combinedExecutions.length - visibleLogCount} remaining)
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT: Trading Metrics (1/3) */}
        <div className="space-y-4">
          {/* Portfolio Value */}
          {tradingState && (
            <div className="p-4 bg-[#0a0a0a] border border-[#1a1a1a]">
              <div className="flex items-center gap-2 mb-4">
                <DollarSign className="h-4 w-4 text-[#00ff00]" />
                <span className="text-xs font-mono text-[#00ff00] font-bold">PORTFOLIO</span>
              </div>
              
              <div className="space-y-4">
                <div>
                  <div className="text-[10px] text-[#006600] font-mono mb-1">TOTAL VALUE</div>
                  <div className="text-2xl font-bold text-[#00ff00] font-mono">
                    ${tradingState.total_portfolio_value.toFixed(2)}
                  </div>
                  <div className="text-[10px] text-[#004400] font-mono">
                    Initial: ${tradingState.initial_capital.toFixed(2)}
                  </div>
                </div>

                <div className="h-px bg-[#1a1a1a]" />

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <div className="text-[10px] text-[#006600] font-mono mb-1">P&L</div>
                    <div className={`text-lg font-bold font-mono flex items-center gap-1 ${
                      tradingState.unrealized_pnl >= 0 ? 'text-[#00ff00]' : 'text-[#ff3333]'
                    }`}>
                      {tradingState.unrealized_pnl >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                      {tradingState.unrealized_pnl >= 0 ? '+' : ''}${tradingState.unrealized_pnl.toFixed(2)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-[#006600] font-mono mb-1">ROI</div>
                    <div className={`text-lg font-bold font-mono ${
                      tradingState.unrealized_pnl_pct >= 0 ? 'text-[#00ff00]' : 'text-[#ff3333]'
                    }`}>
                      {tradingState.unrealized_pnl_pct >= 0 ? '+' : ''}{tradingState.unrealized_pnl_pct.toFixed(2)}%
                    </div>
                  </div>
                </div>

                <div className="h-px bg-[#1a1a1a]" />

                <div>
                  <div className="text-[10px] text-[#006600] font-mono mb-1">ACTIVE POSITIONS</div>
                  <div className="text-lg font-bold text-[#00ff00] font-mono">
                    {tradingState.active_positions}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Trade Statistics */}
          {statistics && statistics.total_trades > 0 && (
            <div className="p-4 bg-[#0a0a0a] border border-[#1a1a1a]">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="h-4 w-4 text-[#00ff00]" />
                <span className="text-xs font-mono text-[#00ff00] font-bold">STATISTICS</span>
              </div>

              <div className="space-y-3">
                {/* Win Rate */}
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-[#006600] font-mono">WIN RATE</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-2 bg-[#1a1a1a] overflow-hidden">
                      <div 
                        className={`h-full ${statistics.win_rate >= 50 ? 'bg-[#00ff00]' : 'bg-[#ff3333]'}`}
                        style={{ width: `${statistics.win_rate}%` }}
                      />
                    </div>
                    <span className={`text-sm font-bold font-mono ${
                      statistics.win_rate >= 50 ? 'text-[#00ff00]' : 'text-[#ff3333]'
                    }`}>
                      {statistics.win_rate.toFixed(1)}%
                    </span>
                  </div>
                </div>

                {/* Total Trades */}
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-[#006600] font-mono">TOTAL TRADES</span>
                  <span className="text-sm font-bold text-[#00ff00] font-mono">
                    {statistics.total_trades}
                  </span>
                </div>

                {/* W/L */}
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-[#006600] font-mono">W / L</span>
                  <span className="text-sm font-mono">
                    <span className="text-[#00ff00] font-bold">{statistics.winning_trades}</span>
                    <span className="text-[#666]"> / </span>
                    <span className="text-[#ff3333] font-bold">{statistics.losing_trades}</span>
                  </span>
                </div>

                <div className="h-px bg-[#1a1a1a]" />

                {/* Net P&L */}
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-[#006600] font-mono">NET P&L</span>
                  <span className={`text-sm font-bold font-mono ${
                    statistics.net_pnl >= 0 ? 'text-[#00ff00]' : 'text-[#ff3333]'
                  }`}>
                    {statistics.net_pnl >= 0 ? '+' : ''}${statistics.net_pnl.toFixed(2)}
                  </span>
                </div>

                {/* Sharpe */}
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-[#006600] font-mono">SHARPE RATIO</span>
                  <span className={`text-sm font-bold font-mono ${
                    (statistics.sharpe_ratio || 0) >= 1 ? 'text-[#00ff00]' : 'text-[#ffff00]'
                  }`}>
                    {(statistics.sharpe_ratio || 0).toFixed(2)}
                  </span>
                </div>

                {/* Max Drawdown */}
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-[#006600] font-mono">MAX DRAWDOWN</span>
                  <span className="text-sm font-bold text-[#ff3333] font-mono">
                    -{(statistics.max_drawdown_pct || 0).toFixed(1)}%
                  </span>
                </div>

                <div className="h-px bg-[#1a1a1a]" />

                {/* Best/Worst */}
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-[#006600] font-mono">BEST TRADE</span>
                  <span className="text-sm font-bold text-[#00ff00] font-mono">
                    +${statistics.largest_win.toFixed(2)}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-[#006600] font-mono">WORST TRADE</span>
                  <span className="text-sm font-bold text-[#ff3333] font-mono">
                    -${Math.abs(statistics.largest_loss).toFixed(2)}
                  </span>
                </div>

                {/* Profit Factor */}
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-[#006600] font-mono">PROFIT FACTOR</span>
                  <span className={`text-sm font-bold font-mono ${
                    (statistics.profit_factor || 0) >= 1 ? 'text-[#00ff00]' : 'text-[#ff3333]'
                  }`}>
                    {(statistics.profit_factor || 0).toFixed(2)}
                  </span>
                </div>

                {/* Expectancy */}
                <div className="flex justify-between items-center">
                  <span className="text-[10px] text-[#006600] font-mono">EXPECTANCY</span>
                  <span className={`text-sm font-bold font-mono ${
                    (statistics.expectancy || 0) >= 0 ? 'text-[#00ff00]' : 'text-[#ff3333]'
                  }`}>
                    {(statistics.expectancy || 0) >= 0 ? '+' : ''}${(statistics.expectancy || 0).toFixed(2)}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Active Positions */}
          {tradingState && tradingState.balances && tradingState.balances.filter(b => b.token_symbol !== "USDC" && b.balance > 0).length > 0 && (
            <div className="p-4 bg-[#0a0a0a] border border-[#1a1a1a]">
              <div className="flex items-center gap-2 mb-3">
                <Activity className="h-4 w-4 text-[#00ff00]" />
                <span className="text-xs font-mono text-[#00ff00] font-bold">POSITIONS</span>
              </div>
              <div className="space-y-2">
                {tradingState.balances
                  .filter(b => b.token_symbol !== "USDC" && b.balance > 0)
                  .map((balance, idx) => (
                    <div key={idx} className="flex justify-between items-center p-2 bg-black border border-[#1a1a1a]">
                      <div>
                        <span className="text-xs text-[#00ff00] font-mono font-bold">{balance.token_symbol}</span>
                        <div className="text-[9px] text-[#006600] font-mono">{balance.balance.toFixed(4)}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-xs text-[#00ff00] font-mono">${balance.usd_value.toFixed(2)}</div>
                        <div className={`text-[9px] font-mono ${
                          (balance.unrealized_pnl || 0) >= 0 ? 'text-[#00ff00]' : 'text-[#ff3333]'
                        }`}>
                          {(balance.unrealized_pnl || 0) >= 0 ? '+' : ''}${(balance.unrealized_pnl || 0).toFixed(2)}
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {!tradingState && !statistics && (
            <div className="p-8 bg-[#0a0a0a] border border-[#1a1a1a] border-dashed text-center">
              <BarChart3 className="h-8 w-8 text-[#006600] mx-auto mb-3 opacity-30" />
              <p className="text-[#006600] font-mono text-xs">
                Select a strategy to view metrics
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
