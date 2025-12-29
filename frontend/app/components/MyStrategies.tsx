"use client";

import { useState, useEffect, useMemo, useRef } from "react";
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
  Circle
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

export function MyStrategies() {
  const { authenticated, getAccessToken } = usePrivyWallet();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategyId, setSelectedStrategyId] = useState<string | null>(null);
  const [tradingState, setTradingState] = useState<TradingState | null>(null);
  const [allExecutions, setAllExecutions] = useState<Map<string, Execution[]>>(new Map());
  const [statistics, setStatistics] = useState<TradeStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [logFilter, setLogFilter] = useState<LogFilter>("all");
  const [expandedStrategy, setExpandedStrategy] = useState<string | null>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [highlightedLogId, setHighlightedLogId] = useState<string | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadStrategies();
  }, [authenticated]);

  useEffect(() => {
    if (strategies.length > 0) {
      loadAllExecutions();
    }
  }, [strategies]);

  useEffect(() => {
    if (selectedStrategyId) {
      loadTradingState();
      loadStatistics();
    }
  }, [selectedStrategyId]);

  useEffect(() => {
    if (autoScroll && feedRef.current) {
      feedRef.current.scrollTop = 0;
    }
  }, [allExecutions, autoScroll]);

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
        const data = await getExecutions(strategy.id, token || undefined, { limit: 30 });
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
        setSelectedStrategyId(null);
        setTradingState(null);
      }
      await loadStrategies();
    } catch (error) {
      console.error("Failed to delete strategy:", error);
      alert("Failed to delete strategy. Please try again.");
    }
  };

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

  const activeCount = strategies.filter(s => s.is_active).length;

  return (
    <div className="space-y-4 h-full flex flex-col">
      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* LIVE EXECUTION FEED - PRIMARY FOCUS */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      <div className="flex-1 min-h-0 flex flex-col">
        {/* Feed Header */}
        <div className="bg-[#0d0d0d] border border-[#1a1a1a] border-b-0">
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
                <span className="text-sm font-mono text-[#00ff00] font-bold tracking-wider">
                  EXECUTION_FEED
                </span>
                <span className="text-xs text-[#006600] font-mono">
                  — live
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {activeCount > 0 && (
                <div className="flex items-center gap-1.5 px-2 py-1 bg-[#00ff00]/10 border border-[#00ff00]/30">
                  <Radio className="h-3 w-3 text-[#00ff00] animate-pulse" />
                  <span className="text-[10px] font-mono text-[#00ff00]">
                    {activeCount} ACTIVE
                  </span>
                </div>
              )}
              <Button
                onClick={() => { loadStrategies(); loadAllExecutions(); }}
                size="sm"
                variant="ghost"
                className="h-7 text-[#00ff00] hover:bg-[#00ff00]/10"
              >
                <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="flex items-center justify-between px-4 py-2">
            <div className="flex items-center gap-1">
              <Filter className="h-3 w-3 text-[#006600] mr-2" />
              {(["all", "buys", "sells", "holds"] as LogFilter[]).map((filter) => (
                <button
                  key={filter}
                  onClick={() => setLogFilter(filter)}
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
            <div className="flex items-center gap-3 text-[10px] font-mono text-[#006600]">
              <span>{combinedExecutions.length} entries</span>
              <button
                onClick={() => setAutoScroll(!autoScroll)}
                className={`flex items-center gap-1 ${autoScroll ? 'text-[#00ff00]' : 'text-[#666]'}`}
              >
                <Activity className="h-3 w-3" />
                {autoScroll ? 'AUTO' : 'PAUSED'}
              </button>
            </div>
          </div>
        </div>

        {/* Feed Content */}
        <div 
          ref={feedRef}
          className="flex-1 bg-[#080808] border border-[#1a1a1a] border-t-0 overflow-y-auto relative"
          style={{ minHeight: '400px' }}
        >
          {/* Scanline Effect */}
          <div className="absolute inset-0 pointer-events-none opacity-[0.02] bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,255,0,0.03)_2px,rgba(0,255,0,0.03)_4px)]" />
          
          {loading && combinedExecutions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full">
              <Loader2 className="h-8 w-8 text-[#00ff00] animate-spin mb-4" />
              <p className="text-[#006600] font-mono text-sm">Initializing feed...</p>
            </div>
          ) : combinedExecutions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full p-8">
              <Terminal className="h-12 w-12 text-[#006600] opacity-30 mb-4" />
              <p className="text-[#006600] font-mono text-sm mb-2">No execution logs yet</p>
              <p className="text-[#004400] font-mono text-xs">
                Start a strategy to see real-time trading decisions
              </p>
            </div>
          ) : (
            <div className="divide-y divide-[#1a1a1a]/50">
              {combinedExecutions.map((execution, index) => (
                <div
                  key={execution.id}
                  className={`group relative transition-all duration-150 ${
                    highlightedLogId === execution.id 
                      ? 'bg-[#00ff00]/5' 
                      : 'hover:bg-[#0f0f0f]'
                  }`}
                  onMouseEnter={() => {
                    setHighlightedLogId(execution.id);
                    setSelectedStrategyId(execution.strategyId);
                  }}
                >
                  {/* New Entry Indicator */}
                  {index === 0 && (
                    <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-[#00ff00] animate-pulse" />
                  )}
                  
                  <div className="px-4 py-3">
                    {/* Log Line Header */}
                    <div className="flex items-start gap-3">
                      {/* Timestamp */}
                      <div className="flex-shrink-0 w-20 text-right">
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
                      <button
                        onClick={() => setExpandedStrategy(expandedStrategy === execution.strategyId ? null : execution.strategyId)}
                        className="flex-shrink-0 px-2 py-1 bg-[#1a1a1a] border border-[#333] hover:border-[#00ff00]/50 transition-colors"
                      >
                        <span className="text-[10px] font-mono text-[#00ff00]">
                          {execution.strategyName}
                        </span>
                      </button>

                      {/* Confidence */}
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-[#1a1a1a] overflow-hidden">
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

                      {/* Trade Executed Badge */}
                      {execution.trade_executed && (
                        <div className="flex items-center gap-1 px-2 py-0.5 bg-[#00ff00]/10 border border-[#00ff00]/30">
                          <Zap className="h-2.5 w-2.5 text-[#00ff00]" />
                          <span className="text-[9px] font-mono text-[#00ff00]">EXECUTED</span>
                        </div>
                      )}
                    </div>

                    {/* Reasoning */}
                    {execution.reasoning && (
                      <div className="mt-2 ml-[92px] text-xs font-mono text-[#006600] leading-relaxed">
                        <span className="text-[#00ff00] mr-2">&gt;</span>
                        {execution.reasoning}
                      </div>
                    )}

                    {/* Trade Details */}
                    {execution.trade_executed && execution.price && (
                      <div className="mt-2 ml-[92px] flex items-center gap-4 text-[10px] font-mono">
                        <div className="flex items-center gap-1">
                          <span className="text-[#006600]">IN:</span>
                          <span className="text-[#00ff00]">
                            {execution.side === "buy" 
                              ? `$${execution.amount_in?.toFixed(2)}` 
                              : `${execution.amount_in?.toFixed(4)}`}
                          </span>
                        </div>
                        <div className="text-[#333]">→</div>
                        <div className="flex items-center gap-1">
                          <span className="text-[#006600]">OUT:</span>
                          <span className="text-[#00ff00]">
                            {execution.side === "buy" 
                              ? `${execution.amount_out?.toFixed(4)}`
                              : `$${execution.amount_out?.toFixed(2)}`}
                          </span>
                        </div>
                        <div className="text-[#333]">@</div>
                        <div className="flex items-center gap-1">
                          <span className="text-[#006600]">PRICE:</span>
                          <span className="text-[#00ff00]">${execution.price?.toFixed(4)}</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* STRATEGY CONTROL DOCK - SECONDARY */}
      {/* ═══════════════════════════════════════════════════════════════════ */}
      <div className="flex-shrink-0 bg-[#0a0a0a] border border-[#1a1a1a]">
        {/* Dock Header */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-[#1a1a1a]">
          <div className="flex items-center gap-2">
            <Cpu className="h-3 w-3 text-[#006600]" />
            <span className="text-xs font-mono text-[#006600]">STRATEGY_DOCK</span>
            <span className="text-[10px] text-[#004400] font-mono">({strategies.length})</span>
          </div>
        </div>

        {/* Strategy Pills */}
        {strategies.length === 0 ? (
          <div className="p-4 text-center">
            <p className="text-[#006600] font-mono text-xs">
              No strategies. Create one in ./strategies
            </p>
          </div>
        ) : (
          <div className="p-3">
            <div className="flex flex-wrap gap-2">
              {strategies.map((strategy) => (
                <div
                  key={strategy.id}
                  className={`group relative transition-all ${
                    selectedStrategyId === strategy.id
                      ? 'ring-1 ring-[#00ff00]'
                      : ''
                  }`}
                >
                  {/* Compact Strategy Pill */}
                  <div 
                    className={`flex items-center gap-2 px-3 py-2 bg-[#111] border transition-all cursor-pointer ${
                      strategy.is_active 
                        ? 'border-[#00ff00]/50 hover:border-[#00ff00]'
                        : 'border-[#333] hover:border-[#666]'
                    }`}
                    onClick={() => setExpandedStrategy(expandedStrategy === strategy.id ? null : strategy.id)}
                  >
                    {/* Status LED */}
                    <div className={`w-2 h-2 rounded-full ${
                      strategy.is_active 
                        ? 'bg-[#00ff00] shadow-[0_0_6px_rgba(0,255,0,0.5)] animate-pulse' 
                        : 'bg-[#333]'
                    }`} />
                    
                    {/* Name */}
                    <span className={`text-xs font-mono font-bold ${
                      strategy.is_active ? 'text-[#00ff00]' : 'text-[#666]'
                    }`}>
                      {strategy.name}
                    </span>

                    {/* Interval */}
                    <span className="text-[9px] font-mono text-[#006600]">
                      {strategy.execution_interval || 5}m
                    </span>

                    {/* Start/Pause Button */}
                    {strategy.is_active ? (
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeactivate(strategy.id);
                        }}
                        size="sm"
                        className="h-6 px-2 bg-transparent text-[#ff3333] hover:bg-[#ff3333]/20 border border-[#ff3333]/50"
                      >
                        <Pause className="h-3 w-3" />
                      </Button>
                    ) : (
                      <Button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleActivate(strategy.id, strategy.execution_interval);
                        }}
                        size="sm"
                        className="h-6 px-2 bg-transparent text-[#00ff00] hover:bg-[#00ff00]/20 border border-[#00ff00]/50"
                      >
                        <Play className="h-3 w-3" />
                      </Button>
                    )}

                    {/* Expand Indicator */}
                    {expandedStrategy === strategy.id ? (
                      <ChevronUp className="h-3 w-3 text-[#006600]" />
                    ) : (
                      <ChevronDown className="h-3 w-3 text-[#006600]" />
                    )}
                  </div>

                  {/* Expanded Drawer */}
                  {expandedStrategy === strategy.id && (
                    <div className="absolute bottom-full left-0 mb-2 w-72 p-4 bg-[#0a0a0a] border border-[#00ff00]/30 shadow-[0_0_20px_rgba(0,255,0,0.1)] z-10">
                      <div className="space-y-3">
                        {/* Description */}
                        {strategy.description && (
                          <p className="text-[10px] text-[#006600] font-mono line-clamp-3">
                            {strategy.description}
                          </p>
                        )}

                        {/* Stats Grid */}
                        {tradingState && selectedStrategyId === strategy.id && (
                          <div className="grid grid-cols-2 gap-2">
                            <div className="p-2 bg-black border border-[#1a1a1a]">
                              <div className="text-[8px] text-[#006600] font-mono">PORTFOLIO</div>
                              <div className="text-sm font-bold text-[#00ff00] font-mono">
                                ${tradingState.total_portfolio_value.toFixed(2)}
                              </div>
                            </div>
                            <div className="p-2 bg-black border border-[#1a1a1a]">
                              <div className="text-[8px] text-[#006600] font-mono">P&L</div>
                              <div className={`text-sm font-bold font-mono flex items-center gap-1 ${
                                tradingState.unrealized_pnl >= 0 ? 'text-[#00ff00]' : 'text-[#ff3333]'
                              }`}>
                                {tradingState.unrealized_pnl >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                                {tradingState.unrealized_pnl >= 0 ? '+' : ''}${tradingState.unrealized_pnl.toFixed(2)}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Performance */}
                        {statistics && statistics.total_trades > 0 && selectedStrategyId === strategy.id && (
                          <div className="grid grid-cols-3 gap-2 text-center">
                            <div className="p-1.5 bg-black border border-[#1a1a1a]">
                              <div className="text-[8px] text-[#006600] font-mono">WIN</div>
                              <div className={`text-xs font-bold font-mono ${
                                statistics.win_rate >= 50 ? 'text-[#00ff00]' : 'text-[#ff3333]'
                              }`}>
                                {statistics.win_rate.toFixed(0)}%
                              </div>
                            </div>
                            <div className="p-1.5 bg-black border border-[#1a1a1a]">
                              <div className="text-[8px] text-[#006600] font-mono">TRADES</div>
                              <div className="text-xs font-bold text-[#00ff00] font-mono">
                                {statistics.total_trades}
                              </div>
                            </div>
                            <div className="p-1.5 bg-black border border-[#1a1a1a]">
                              <div className="text-[8px] text-[#006600] font-mono">SHARPE</div>
                              <div className="text-xs font-bold text-[#00ff00] font-mono">
                                {(statistics.sharpe_ratio || 0).toFixed(2)}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Actions */}
                        <div className="flex items-center gap-2 pt-2 border-t border-[#1a1a1a]">
                          <div className="flex items-center gap-1 text-[9px] text-[#006600] font-mono">
                            <Clock className="h-3 w-3" />
                            <span>
                              {(strategy.strategy_config?.llm_provider || "deepseek/deepseek-r1").split("/").pop()}
                            </span>
                          </div>
                          <div className="flex-1" />
                          <Button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDelete(strategy.id);
                            }}
                            size="sm"
                            variant="ghost"
                            className="h-6 px-2 text-[#ff3333] hover:bg-[#ff3333]/20"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
