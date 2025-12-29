"use client";

import { useState, useEffect, useMemo } from "react";
import { usePrivyWallet } from "@/app/hooks/use-privy-wallet";
import { Button } from "./ui/button";
import {
  Play,
  Pause,
  Trash2,
  Loader2,
  TrendingUp,
  TrendingDown,
  Activity,
  ChevronDown,
  ChevronUp,
  Zap,
  Clock,
  Target,
  BarChart3,
  Terminal,
  Cpu,
  DollarSign,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Eye,
  EyeOff,
  RefreshCw,
  Layers
} from "lucide-react";
import { 
  getStrategies, 
  executeStrategy, 
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

export function MyStrategies() {
  const { authenticated, getAccessToken } = usePrivyWallet();
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [tradingState, setTradingState] = useState<TradingState | null>(null);
  const [executions, setExecutions] = useState<Execution[]>([]);
  const [statistics, setStatistics] = useState<TradeStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  useEffect(() => {
    loadStrategies();
  }, [authenticated]);

  useEffect(() => {
    if (selectedStrategy) {
      loadTradingState();
      loadExecutions();
      loadStatistics();
    }
  }, [selectedStrategy]);

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

  const loadTradingState = async () => {
    if (!selectedStrategy) return;
    try {
      const token = authenticated ? await getAccessToken() : undefined;
      const state = await getTradingState(selectedStrategy.id, token || undefined);
      setTradingState(state);
    } catch (error) {
      console.error("Failed to load trading state:", error);
    }
  };

  const loadExecutions = async () => {
    if (!selectedStrategy) return;
    try {
      const token = authenticated ? await getAccessToken() : undefined;
      const data = await getExecutions(selectedStrategy.id, token || undefined, { limit: 20 });
      setExecutions(data.executions);
    } catch (error) {
      console.error("Failed to load executions:", error);
    }
  };

  const loadStatistics = async () => {
    if (!selectedStrategy) return;
    try {
      const token = authenticated ? await getAccessToken() : undefined;
      const data = await getTradeStatistics(selectedStrategy.id, token || undefined);
      setStatistics(data.statistics);
    } catch (error) {
      console.error("Failed to load statistics:", error);
      setStatistics(null);
    }
  };

  const handleExecute = async () => {
    if (!selectedStrategy) return;
    try {
      setExecuting(true);
      const token = authenticated ? await getAccessToken() : undefined;
      await executeStrategy(selectedStrategy.id, "analysis", token || undefined);
      await loadTradingState();
      await loadExecutions();
    } catch (error) {
      console.error("Failed to execute strategy:", error);
      alert("Failed to execute strategy. Please try again.");
    } finally {
      setExecuting(false);
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
      if (selectedStrategy?.id === strategyId) {
        setSelectedStrategy(null);
        setTradingState(null);
        setExecutions([]);
      }
      await loadStrategies();
    } catch (error) {
      console.error("Failed to delete strategy:", error);
      alert("Failed to delete strategy. Please try again.");
    }
  };

  const activeStrategies = useMemo(() => strategies.filter(s => s.is_active), [strategies]);
  const inactiveStrategies = useMemo(() => strategies.filter(s => !s.is_active), [strategies]);

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case "BUY": return <ArrowUpRight className="h-3 w-3" />;
      case "SELL": return <ArrowDownRight className="h-3 w-3" />;
      default: return <Minus className="h-3 w-3" />;
    }
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="relative">
        <div className="absolute -top-2 -left-2 w-3 h-3 border-t-2 border-l-2 border-[#00ff00]" />
        <div className="absolute -top-2 -right-2 w-3 h-3 border-t-2 border-r-2 border-[#00ff00]" />
        <div className="p-6 bg-gradient-to-b from-[#0a0a0a] to-black border border-[#1a1a1a]">
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 bg-[#00ff00]/10 border border-[#00ff00]/30">
                  <Layers className="h-5 w-5 text-[#00ff00]" />
                </div>
                <h1 className="text-2xl font-bold text-[#00ff00] font-mono tracking-wider">
                  MY_STRATEGIES
                </h1>
              </div>
              <p className="text-xs text-[#006600] font-mono flex items-center gap-2">
                <Terminal className="h-3 w-3" />
                <span>Manage and monitor your AI trading strategies</span>
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <div className="text-[10px] text-[#006600] font-mono">TOTAL</div>
                <div className="text-lg text-[#00ff00] font-mono font-bold">{strategies.length}</div>
              </div>
              <div className="w-px h-10 bg-[#1a1a1a]" />
              <div className="text-right">
                <div className="text-[10px] text-[#006600] font-mono">ACTIVE</div>
                <div className="text-lg text-[#00ff00] font-mono font-bold">{activeStrategies.length}</div>
              </div>
              <Button
                onClick={loadStrategies}
                size="sm"
                variant="ghost"
                className="text-[#00ff00] hover:bg-[#00ff00]/10"
              >
                <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
        </div>
        <div className="absolute -bottom-2 -left-2 w-3 h-3 border-b-2 border-l-2 border-[#00ff00]" />
        <div className="absolute -bottom-2 -right-2 w-3 h-3 border-b-2 border-r-2 border-[#00ff00]" />
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* LEFT: Strategy Cards (Primary Focus - takes 2 columns) */}
        <div className="xl:col-span-2 space-y-6">
          {loading && strategies.length === 0 ? (
            <div className="flex items-center justify-center p-20 bg-[#0a0a0a] border border-[#1a1a1a]">
              <div className="text-center">
                <Loader2 className="h-8 w-8 text-[#00ff00] animate-spin mx-auto mb-4" />
                <p className="text-[#006600] font-mono text-sm">Loading strategies...</p>
              </div>
            </div>
          ) : strategies.length === 0 ? (
            <div className="p-20 text-center bg-[#0a0a0a] border border-[#1a1a1a] border-dashed">
              <Activity className="h-12 w-12 text-[#006600] mx-auto mb-4 opacity-50" />
              <p className="text-[#006600] font-mono text-sm mb-2">No strategies found</p>
              <p className="text-[#004400] font-mono text-xs">
                Create your first strategy in the ./strategies tab
              </p>
            </div>
          ) : (
            <>
              {/* Active Strategies Section */}
              {activeStrategies.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-[#00ff00] animate-pulse" />
                      <span className="text-sm font-mono text-[#00ff00] font-bold">RUNNING</span>
                    </div>
                    <div className="flex-1 h-px bg-gradient-to-r from-[#00ff00]/50 to-transparent" />
                    <span className="text-xs text-[#006600] font-mono">{activeStrategies.length} active</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {activeStrategies.map((strategy) => (
                      <StrategyCard
                        key={strategy.id}
                        strategy={strategy}
                        isSelected={selectedStrategy?.id === strategy.id}
                        onSelect={() => setSelectedStrategy(strategy)}
                        onActivate={handleActivate}
                        onDeactivate={handleDeactivate}
                        onDelete={handleDelete}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Inactive Strategies Section */}
              {inactiveStrategies.length > 0 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-[#666]" />
                      <span className="text-sm font-mono text-[#666] font-bold">INACTIVE</span>
                    </div>
                    <div className="flex-1 h-px bg-gradient-to-r from-[#333] to-transparent" />
                    <span className="text-xs text-[#666] font-mono">{inactiveStrategies.length} paused</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {inactiveStrategies.map((strategy) => (
                      <StrategyCard
                        key={strategy.id}
                        strategy={strategy}
                        isSelected={selectedStrategy?.id === strategy.id}
                        onSelect={() => setSelectedStrategy(strategy)}
                        onActivate={handleActivate}
                        onDeactivate={handleDeactivate}
                        onDelete={handleDelete}
                      />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* RIGHT: Quick Stats Panel */}
        <div className="space-y-4">
          {selectedStrategy ? (
            <>
              {/* Selected Strategy Header */}
              <div className="p-4 bg-[#0a0a0a] border border-[#00ff00]/50 shadow-[0_0_20px_rgba(0,255,0,0.1)]">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Cpu className="h-4 w-4 text-[#00ff00]" />
                    <span className="text-sm font-mono text-[#00ff00] font-bold truncate">
                      {selectedStrategy.name}
                    </span>
                  </div>
                  {selectedStrategy.is_active && (
                    <span className="px-2 py-0.5 text-[9px] bg-[#00ff00] text-black font-mono font-bold">
                      LIVE
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    onClick={handleExecute}
                    disabled={executing}
                    size="sm"
                    className="flex-1 bg-[#00ff00] text-black hover:bg-[#00cc00] font-mono text-xs h-8"
                  >
                    {executing ? (
                      <>
                        <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        RUNNING
                      </>
                    ) : (
                      <>
                        <Zap className="h-3 w-3 mr-1" />
                        EXECUTE
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={() => loadExecutions()}
                    size="sm"
                    variant="ghost"
                    className="text-[#00ff00] hover:bg-[#00ff00]/10 h-8"
                  >
                    <RefreshCw className="h-3 w-3" />
                  </Button>
                </div>
              </div>

              {/* Portfolio Stats */}
              {tradingState && (
                <div className="p-4 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="flex items-center gap-2 mb-4">
                    <BarChart3 className="h-4 w-4 text-[#00ff00]" />
                    <span className="text-xs font-mono text-[#00ff00]">PORTFOLIO</span>
                  </div>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] text-[#006600] font-mono">VALUE</span>
                      <span className="text-lg font-bold text-[#00ff00] font-mono">
                        ${tradingState.total_portfolio_value.toFixed(2)}
                      </span>
                    </div>
                    <div className="h-px bg-[#1a1a1a]" />
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] text-[#006600] font-mono">P&L</span>
                      <div className={`flex items-center gap-1 font-mono text-sm font-bold ${
                        tradingState.unrealized_pnl >= 0 ? "text-[#00ff00]" : "text-[#ff0000]"
                      }`}>
                        {tradingState.unrealized_pnl >= 0 ? (
                          <TrendingUp className="h-3 w-3" />
                        ) : (
                          <TrendingDown className="h-3 w-3" />
                        )}
                        {tradingState.unrealized_pnl >= 0 ? "+" : ""}
                        ${tradingState.unrealized_pnl.toFixed(2)}
                      </div>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] text-[#006600] font-mono">ROI</span>
                      <span className={`font-mono text-sm font-bold ${
                        tradingState.unrealized_pnl_pct >= 0 ? "text-[#00ff00]" : "text-[#ff0000]"
                      }`}>
                        {tradingState.unrealized_pnl_pct >= 0 ? "+" : ""}
                        {tradingState.unrealized_pnl_pct.toFixed(2)}%
                      </span>
                    </div>
                    <div className="h-px bg-[#1a1a1a]" />
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] text-[#006600] font-mono">POSITIONS</span>
                      <span className="text-sm font-bold text-[#00ff00] font-mono">
                        {tradingState.active_positions}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Trade Stats */}
              {statistics && statistics.total_trades > 0 && (
                <div className="p-4 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="flex items-center gap-2 mb-4">
                    <Target className="h-4 w-4 text-[#00ff00]" />
                    <span className="text-xs font-mono text-[#00ff00]">PERFORMANCE</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-2 bg-black/50 border border-[#1a1a1a]">
                      <div className="text-[9px] text-[#006600] font-mono mb-1">WIN RATE</div>
                      <div className={`text-sm font-bold font-mono ${
                        statistics.win_rate >= 50 ? "text-[#00ff00]" : "text-[#ff0000]"
                      }`}>
                        {statistics.win_rate.toFixed(1)}%
                      </div>
                    </div>
                    <div className="p-2 bg-black/50 border border-[#1a1a1a]">
                      <div className="text-[9px] text-[#006600] font-mono mb-1">TRADES</div>
                      <div className="text-sm font-bold text-[#00ff00] font-mono">
                        {statistics.total_trades}
                      </div>
                    </div>
                    <div className="p-2 bg-black/50 border border-[#1a1a1a]">
                      <div className="text-[9px] text-[#006600] font-mono mb-1">SHARPE</div>
                      <div className={`text-sm font-bold font-mono ${
                        (statistics.sharpe_ratio || 0) >= 1 ? "text-[#00ff00]" : "text-[#ffff00]"
                      }`}>
                        {(statistics.sharpe_ratio || 0).toFixed(2)}
                      </div>
                    </div>
                    <div className="p-2 bg-black/50 border border-[#1a1a1a]">
                      <div className="text-[9px] text-[#006600] font-mono mb-1">MAX DD</div>
                      <div className="text-sm font-bold text-[#ff0000] font-mono">
                        -{(statistics.max_drawdown_pct || 0).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Active Positions */}
              {tradingState && tradingState.balances && tradingState.balances.filter(b => b.token_symbol !== "USDC" && b.balance > 0).length > 0 && (
                <div className="p-4 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="flex items-center gap-2 mb-3">
                    <DollarSign className="h-4 w-4 text-[#00ff00]" />
                    <span className="text-xs font-mono text-[#00ff00]">POSITIONS</span>
                  </div>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {tradingState.balances
                      .filter(b => b.token_symbol !== "USDC" && b.balance > 0)
                      .map((balance, idx) => (
                        <div key={idx} className="flex justify-between items-center p-2 bg-black/50 border border-[#1a1a1a]">
                          <div>
                            <span className="text-xs text-[#00ff00] font-mono font-bold">{balance.token_symbol}</span>
                            <div className="text-[9px] text-[#006600] font-mono">{balance.balance.toFixed(4)}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-xs text-[#00ff00] font-mono">${balance.usd_value.toFixed(2)}</div>
                            <div className={`text-[9px] font-mono ${
                              (balance.unrealized_pnl || 0) >= 0 ? "text-[#00ff00]" : "text-[#ff0000]"
                            }`}>
                              {(balance.unrealized_pnl || 0) >= 0 ? "+" : ""}${(balance.unrealized_pnl || 0).toFixed(2)}
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="p-8 bg-[#0a0a0a] border border-[#1a1a1a] border-dashed text-center">
              <Eye className="h-8 w-8 text-[#006600] mx-auto mb-3 opacity-50" />
              <p className="text-[#006600] font-mono text-xs">
                Select a strategy to view details
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Execution Logs Section (Secondary - Collapsible) */}
      {selectedStrategy && (
        <div className="border border-[#1a1a1a] bg-[#0a0a0a]">
          <button
            onClick={() => setShowLogs(!showLogs)}
            className="w-full p-4 flex items-center justify-between hover:bg-[#0f0f0f] transition-colors"
          >
            <div className="flex items-center gap-3">
              <Terminal className="h-4 w-4 text-[#006600]" />
              <span className="text-sm font-mono text-[#006600]">EXECUTION_LOGS</span>
              <span className="text-xs text-[#004400] font-mono">({executions.length} entries)</span>
            </div>
            <div className="flex items-center gap-2">
              {showLogs ? (
                <>
                  <span className="text-[10px] text-[#006600] font-mono">COLLAPSE</span>
                  <ChevronUp className="h-4 w-4 text-[#006600]" />
                </>
              ) : (
                <>
                  <span className="text-[10px] text-[#006600] font-mono">EXPAND</span>
                  <ChevronDown className="h-4 w-4 text-[#006600]" />
                </>
              )}
            </div>
          </button>

          {showLogs && (
            <div className="border-t border-[#1a1a1a]">
              {executions.length === 0 ? (
                <div className="p-8 text-center">
                  <p className="text-[#006600] font-mono text-xs">
                    No executions yet. Click EXECUTE to run the strategy.
                  </p>
                </div>
              ) : (
                <div className="divide-y divide-[#1a1a1a] max-h-[400px] overflow-y-auto">
                  {executions.map((execution) => (
                    <div
                      key={execution.id}
                      className="hover:bg-[#0f0f0f] transition-colors"
                    >
                      <button
                        onClick={() => setExpandedLogId(expandedLogId === execution.id ? null : execution.id)}
                        className="w-full p-3 flex items-center justify-between text-left"
                      >
                        <div className="flex items-center gap-3">
                          <div className={`p-1.5 border ${
                            execution.decision === "BUY"
                              ? "bg-[#00ff00]/10 border-[#00ff00]/50 text-[#00ff00]"
                              : execution.decision === "SELL"
                              ? "bg-[#ff0000]/10 border-[#ff0000]/50 text-[#ff0000]"
                              : "bg-[#666]/10 border-[#666]/50 text-[#666]"
                          }`}>
                            {getDecisionIcon(execution.decision)}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className={`text-xs font-mono font-bold ${
                                execution.decision === "BUY" ? "text-[#00ff00]" :
                                execution.decision === "SELL" ? "text-[#ff0000]" : "text-[#666]"
                              }`}>
                                {execution.decision}
                              </span>
                              <span className="text-[10px] text-[#006600] font-mono">
                                {(execution.confidence * 100).toFixed(0)}% conf
                              </span>
                              {execution.trade_executed && (
                                <span className="px-1.5 py-0.5 text-[8px] bg-[#00ff00]/20 text-[#00ff00] font-mono border border-[#00ff00]/30">
                                  EXECUTED
                                </span>
                              )}
                            </div>
                            <div className="text-[10px] text-[#004400] font-mono">
                              {new Date(execution.execution_timestamp).toLocaleString()}
                            </div>
                          </div>
                        </div>
                        {expandedLogId === execution.id ? (
                          <ChevronUp className="h-4 w-4 text-[#006600]" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-[#006600]" />
                        )}
                      </button>
                      {expandedLogId === execution.id && execution.reasoning && (
                        <div className="px-4 pb-4">
                          <div className="p-3 bg-black border border-[#1a1a1a] text-xs text-[#006600] font-mono leading-relaxed">
                            <span className="text-[#00ff00]">&gt;</span> {execution.reasoning}
                          </div>
                          {execution.trade_executed && execution.price && (
                            <div className="mt-2 grid grid-cols-3 gap-2 text-[10px] font-mono">
                              <div className="p-2 bg-black border border-[#1a1a1a]">
                                <span className="text-[#006600]">AMOUNT_IN:</span>
                                <span className="text-[#00ff00] ml-1">
                                  {execution.side === "buy" 
                                    ? `$${execution.amount_in?.toFixed(2)}` 
                                    : `${execution.amount_in?.toFixed(4)}`}
                                </span>
                              </div>
                              <div className="p-2 bg-black border border-[#1a1a1a]">
                                <span className="text-[#006600]">AMOUNT_OUT:</span>
                                <span className="text-[#00ff00] ml-1">
                                  {execution.side === "buy" 
                                    ? `${execution.amount_out?.toFixed(4)}`
                                    : `$${execution.amount_out?.toFixed(2)}`}
                                </span>
                              </div>
                              <div className="p-2 bg-black border border-[#1a1a1a]">
                                <span className="text-[#006600]">PRICE:</span>
                                <span className="text-[#00ff00] ml-1">${execution.price?.toFixed(4)}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

interface StrategyCardProps {
  strategy: Strategy;
  isSelected: boolean;
  onSelect: () => void;
  onActivate: (id: string, interval?: number) => void;
  onDeactivate: (id: string) => void;
  onDelete: (id: string) => void;
}

function StrategyCard({ strategy, isSelected, onSelect, onActivate, onDeactivate, onDelete }: StrategyCardProps) {
  return (
    <div
      className={`relative group cursor-pointer transition-all duration-200 ${
        isSelected
          ? "bg-[#0a0a0a] border-2 border-[#00ff00] shadow-[0_0_30px_rgba(0,255,0,0.15)]"
          : "bg-[#0a0a0a] border border-[#1a1a1a] hover:border-[#00ff00]/50 hover:shadow-[0_0_15px_rgba(0,255,0,0.05)]"
      }`}
      onClick={onSelect}
    >
      {/* Status indicator bar */}
      <div className={`absolute top-0 left-0 right-0 h-0.5 ${
        strategy.is_active ? "bg-[#00ff00]" : "bg-[#333]"
      }`} />

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              {strategy.is_active && (
                <div className="w-1.5 h-1.5 rounded-full bg-[#00ff00] animate-pulse" />
              )}
              <h3 className="text-sm font-mono text-[#00ff00] font-bold truncate">
                {strategy.name}
              </h3>
            </div>
            {strategy.description && (
              <p className="text-[10px] text-[#006600] font-mono line-clamp-2 leading-relaxed">
                {strategy.description}
              </p>
            )}
          </div>
        </div>

        {/* Info Row */}
        <div className="flex items-center gap-4 mb-4 text-[10px] font-mono text-[#006600]">
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{strategy.execution_interval || 5}m</span>
          </div>
          <div className="flex items-center gap-1">
            <Cpu className="h-3 w-3" />
            <span className="truncate max-w-[100px]">
              {(strategy.strategy_config?.llm_provider || "deepseek/deepseek-r1").split("/").pop()}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {strategy.is_active ? (
            <Button
              onClick={(e) => {
                e.stopPropagation();
                onDeactivate(strategy.id);
              }}
              size="sm"
              className="flex-1 h-8 bg-transparent text-[#ff0000] hover:bg-[#ff0000]/10 border border-[#ff0000]/50 font-mono text-[10px]"
            >
              <Pause className="h-3 w-3 mr-1" />
              PAUSE
            </Button>
          ) : (
            <Button
              onClick={(e) => {
                e.stopPropagation();
                onActivate(strategy.id, strategy.execution_interval);
              }}
              size="sm"
              className="flex-1 h-8 bg-transparent text-[#00ff00] hover:bg-[#00ff00]/10 border border-[#00ff00]/50 font-mono text-[10px]"
            >
              <Play className="h-3 w-3 mr-1" />
              START
            </Button>
          )}
          <Button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(strategy.id);
            }}
            size="sm"
            variant="ghost"
            className="h-8 w-8 p-0 text-[#ff0000] hover:bg-[#ff0000]/10 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <Trash2 className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}
