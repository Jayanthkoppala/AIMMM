"use client";

import { useState, useEffect } from "react";
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
  ChevronRight
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
      // Use the strategy's execution_interval, or default to 5 if not set
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[#00ff00] font-mono glow-text">
          ./my_strategies
        </h1>
        <p className="text-xs text-[#006600] mt-1 font-mono">
          {">"} Manage and monitor your trading strategies
        </p>
      </div>

      {/* My Strategies List */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-[#1a1a1a]">
          <Activity className="h-4 w-4 text-[#00ff00]" />
          <span className="text-sm font-mono text-[#00ff00]">MY_STRATEGIES</span>
          <span className="text-xs text-[#006600] font-mono ml-2">({strategies.length})</span>
        </div>

        {loading && strategies.length === 0 ? (
          <div className="flex items-center justify-center p-12 bg-[#0a0a0a] border border-[#1a1a1a]">
            <Loader2 className="h-6 w-6 text-[#00ff00] animate-spin" />
          </div>
        ) : strategies.length === 0 ? (
          <div className="p-12 text-center bg-[#0a0a0a] border border-[#1a1a1a]">
            <p className="text-[#006600] font-mono text-sm">
              {">"} No strategies found. Create your first strategy in the ./strategies tab.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
            {strategies.map((strategy) => (
              <div
                key={strategy.id}
                className={`p-4 bg-[#0a0a0a] border transition-all cursor-pointer ${
                  selectedStrategy?.id === strategy.id
                    ? "border-[#00ff00] shadow-[0_0_10px_rgba(0,255,0,0.3)]"
                    : "border-[#1a1a1a] hover:border-[#00ff00]/50"
                }`}
                onClick={() => setSelectedStrategy(strategy)}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <h3 className="text-sm font-mono text-[#00ff00] mb-1">
                      {strategy.name}
                    </h3>
                    {strategy.description && (
                      <p className="text-xs text-[#006600] line-clamp-2 font-mono">
                        {strategy.description}
                      </p>
                    )}
                    <div className="text-[10px] text-[#006600] font-mono mt-1">
                      Interval: {strategy.execution_interval || 5} min
                    </div>
                  </div>
                  {strategy.is_active && (
                    <span className="px-2 py-1 text-[10px] bg-[#00ff00]/20 text-[#00ff00] border border-[#00ff00] font-mono">
                      ACTIVE
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2 mt-3">
                  {strategy.is_active ? (
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeactivate(strategy.id);
                      }}
                      size="sm"
                      className="flex-1 bg-[#ff0000]/20 text-[#ff0000] hover:bg-[#ff0000]/30 border border-[#ff0000] font-mono text-xs"
                    >
                      <Pause className="h-3 w-3 mr-1" />
                      STOP
                    </Button>
                  ) : (
                    <Button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleActivate(strategy.id, strategy.execution_interval);
                      }}
                      size="sm"
                      className="flex-1 bg-[#00ff00]/20 text-[#00ff00] hover:bg-[#00ff00]/30 border border-[#00ff00] font-mono text-xs"
                    >
                      <Play className="h-3 w-3 mr-1" />
                      START
                    </Button>
                  )}
                  <Button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(strategy.id);
                    }}
                    size="sm"
                    variant="ghost"
                    className="text-[#ff0000] hover:bg-[#ff0000]/20 font-mono text-xs"
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Trading Dashboard - Shows when strategy is selected */}
      {selectedStrategy && (
        <div className="space-y-6">
          <div className="flex items-center gap-2 pb-3 border-b border-[#1a1a1a]">
            <ChevronRight className="h-4 w-4 text-[#00ff00]" />
            <span className="text-sm font-mono text-[#00ff00]">TRADING_DASHBOARD</span>
            <span className="text-xs text-[#006600] font-mono ml-2">
              {selectedStrategy.name}
            </span>
          </div>

          {/* Performance Stats */}
          {tradingState && (
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-4 bg-[#0a0a0a] border border-[#1a1a1a]">
                <div className="text-xs text-[#006600] font-mono mb-1">PORTFOLIO_VALUE</div>
                <div className="text-lg font-bold text-[#00ff00] font-mono">
                  ${tradingState.total_portfolio_value.toFixed(2)}
                </div>
                <div className="text-[10px] text-[#006600] font-mono mt-1">
                  Initial: ${tradingState.initial_capital.toFixed(2)}
                </div>
              </div>
              <div className="p-4 bg-[#0a0a0a] border border-[#1a1a1a]">
                <div className="text-xs text-[#006600] font-mono mb-1">TOTAL_PNL</div>
                <div className={`text-lg font-bold font-mono flex items-center gap-1 ${
                  tradingState.unrealized_pnl >= 0 ? "text-[#00ff00]" : "text-[#ff0000]"
                }`}>
                  {tradingState.unrealized_pnl >= 0 ? (
                    <TrendingUp className="h-4 w-4" />
                  ) : (
                    <TrendingDown className="h-4 w-4" />
                  )}
                  {tradingState.unrealized_pnl >= 0 ? "+" : "-"}${Math.abs(tradingState.unrealized_pnl).toFixed(2)}
                </div>
                {tradingState.realized_pnl !== undefined && tradingState.realized_pnl !== 0 && (
                  <div className="text-[10px] text-[#006600] font-mono mt-1">
                    Realized: {tradingState.realized_pnl >= 0 ? "+" : "-"}${Math.abs(tradingState.realized_pnl).toFixed(2)}
                  </div>
                )}
              </div>
              <div className="p-4 bg-[#0a0a0a] border border-[#1a1a1a]">
                <div className="text-xs text-[#006600] font-mono mb-1">PNL_PERCENT</div>
                <div className={`text-lg font-bold font-mono ${
                  tradingState.unrealized_pnl_pct >= 0 ? "text-[#00ff00]" : "text-[#ff0000]"
                }`}>
                  {tradingState.unrealized_pnl_pct >= 0 ? "+" : ""}
                  {tradingState.unrealized_pnl_pct.toFixed(2)}%
                </div>
              </div>
              <div className="p-4 bg-[#0a0a0a] border border-[#1a1a1a]">
                <div className="text-xs text-[#006600] font-mono mb-1">ACTIVE_POSITIONS</div>
                <div className="text-lg font-bold text-[#00ff00] font-mono">
                  {tradingState.active_positions}
                </div>
              </div>
            </div>
          )}

          {/* Trade Statistics */}
          {statistics && statistics.total_trades > 0 && (
            <div className="space-y-3">
              <div className="text-xs text-[#006600] font-mono uppercase">TRADE_STATISTICS</div>
              
              {/* Row 1: Core Performance */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="text-[10px] text-[#006600] font-mono mb-1">WIN_RATE</div>
                  <div className={`text-lg font-bold font-mono ${statistics.win_rate >= 50 ? "text-[#00ff00]" : "text-[#ff0000]"}`}>
                    {statistics.win_rate.toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-[#006600] font-mono">
                    {statistics.winning_trades}W / {statistics.losing_trades}L
                  </div>
                </div>
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="text-[10px] text-[#006600] font-mono mb-1">NET_PNL</div>
                  <div className={`text-lg font-bold font-mono ${statistics.net_pnl >= 0 ? "text-[#00ff00]" : "text-[#ff0000]"}`}>
                    {statistics.net_pnl >= 0 ? "+" : ""}${statistics.net_pnl.toFixed(2)}
                  </div>
                  <div className="text-[10px] text-[#006600] font-mono">
                    ROI: {statistics.roi_pct >= 0 ? "+" : ""}{statistics.roi_pct?.toFixed(1) || "0"}%
                  </div>
                </div>
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="text-[10px] text-[#006600] font-mono mb-1">SHARPE_RATIO</div>
                  <div className={`text-lg font-bold font-mono ${(statistics.sharpe_ratio || 0) >= 1 ? "text-[#00ff00]" : (statistics.sharpe_ratio || 0) >= 0 ? "text-[#ffff00]" : "text-[#ff0000]"}`}>
                    {(statistics.sharpe_ratio || 0).toFixed(2)}
                  </div>
                  <div className="text-[10px] text-[#006600] font-mono">
                    {(statistics.sharpe_ratio || 0) >= 2 ? "Excellent" : (statistics.sharpe_ratio || 0) >= 1 ? "Good" : (statistics.sharpe_ratio || 0) >= 0 ? "Moderate" : "Poor"}
                  </div>
                </div>
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="text-[10px] text-[#006600] font-mono mb-1">MAX_DRAWDOWN</div>
                  <div className={`text-lg font-bold font-mono ${(statistics.max_drawdown_pct || 0) <= 10 ? "text-[#00ff00]" : (statistics.max_drawdown_pct || 0) <= 20 ? "text-[#ffff00]" : "text-[#ff0000]"}`}>
                    -{(statistics.max_drawdown_pct || 0).toFixed(1)}%
                  </div>
                  <div className="text-[10px] text-[#006600] font-mono">
                    ${(statistics.max_drawdown || 0).toFixed(2)}
                  </div>
                </div>
              </div>
              
              {/* Row 2: Risk Metrics */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="text-[10px] text-[#006600] font-mono mb-1">SORTINO_RATIO</div>
                  <div className={`text-lg font-bold font-mono ${(statistics.sortino_ratio || 0) >= 1.5 ? "text-[#00ff00]" : (statistics.sortino_ratio || 0) >= 0 ? "text-[#ffff00]" : "text-[#ff0000]"}`}>
                    {(statistics.sortino_ratio || 0).toFixed(2)}
                  </div>
                  <div className="text-[10px] text-[#006600] font-mono">Downside Risk</div>
                </div>
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="text-[10px] text-[#006600] font-mono mb-1">PROFIT_FACTOR</div>
                  <div className={`text-lg font-bold font-mono ${(statistics.profit_factor || 0) >= 1.5 ? "text-[#00ff00]" : (statistics.profit_factor || 0) >= 1 ? "text-[#ffff00]" : "text-[#ff0000]"}`}>
                    {(statistics.profit_factor || 0).toFixed(2)}
                  </div>
                  <div className="text-[10px] text-[#006600] font-mono">Profit / Loss</div>
                </div>
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="text-[10px] text-[#006600] font-mono mb-1">RISK_REWARD</div>
                  <div className={`text-lg font-bold font-mono ${(statistics.risk_reward_ratio || 0) >= 2 ? "text-[#00ff00]" : (statistics.risk_reward_ratio || 0) >= 1 ? "text-[#ffff00]" : "text-[#ff0000]"}`}>
                    {(statistics.risk_reward_ratio || 0).toFixed(2)}:1
                  </div>
                  <div className="text-[10px] text-[#006600] font-mono">Avg Win/Loss</div>
                </div>
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="text-[10px] text-[#006600] font-mono mb-1">EXPECTANCY</div>
                  <div className={`text-lg font-bold font-mono ${(statistics.expectancy || 0) >= 0 ? "text-[#00ff00]" : "text-[#ff0000]"}`}>
                    {(statistics.expectancy || 0) >= 0 ? "+" : ""}${(statistics.expectancy || 0).toFixed(2)}
                  </div>
                  <div className="text-[10px] text-[#006600] font-mono">Per Trade</div>
                </div>
              </div>
              
              {/* Row 3: Trade Details */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="text-[10px] text-[#006600] font-mono mb-1">TOTAL_TRADES</div>
                  <div className="text-lg font-bold text-[#00ff00] font-mono">
                    {statistics.total_trades}
                  </div>
                  <div className="text-[10px] text-[#006600] font-mono">
                    Buys: {statistics.total_buys} | Sells: {statistics.total_sells}
                  </div>
                </div>
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="text-[10px] text-[#006600] font-mono mb-1">BEST/WORST</div>
                  <div className="text-sm font-bold font-mono">
                    <span className="text-[#00ff00]">+${statistics.largest_win.toFixed(2)}</span>
                    <span className="text-[#006600]"> / </span>
                    <span className="text-[#ff0000]">-${Math.abs(statistics.largest_loss).toFixed(2)}</span>
                  </div>
                  <div className="text-[10px] text-[#006600] font-mono">
                    Avg Return: {(statistics.avg_return_pct || 0) >= 0 ? "+" : ""}{(statistics.avg_return_pct || 0).toFixed(1)}%
                  </div>
                </div>
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="text-[10px] text-[#006600] font-mono mb-1">AVG_DURATION</div>
                  <div className="text-lg font-bold text-[#00ff00] font-mono">
                    {(statistics.avg_trade_duration_hours || 0) >= 1 
                      ? `${(statistics.avg_trade_duration_hours || 0).toFixed(1)}h`
                      : `${(statistics.avg_trade_duration_mins || 0).toFixed(0)}m`
                    }
                  </div>
                  <div className="text-[10px] text-[#006600] font-mono">Per Trade</div>
                </div>
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                  <div className="text-[10px] text-[#006600] font-mono mb-1">CALMAR_RATIO</div>
                  <div className={`text-lg font-bold font-mono ${(statistics.calmar_ratio || 0) >= 1 ? "text-[#00ff00]" : (statistics.calmar_ratio || 0) >= 0 ? "text-[#ffff00]" : "text-[#ff0000]"}`}>
                    {(statistics.calmar_ratio || 0).toFixed(2)}
                  </div>
                  <div className="text-[10px] text-[#006600] font-mono">Return/Drawdown</div>
                </div>
              </div>
            </div>
          )}

          {/* Execute Button */}
          <div className="flex items-center gap-4">
            <Button
              onClick={handleExecute}
              disabled={executing}
              className="bg-[#00ff00] text-black hover:bg-[#00cc00] font-mono text-xs"
            >
              {executing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  EXECUTING...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  EXECUTE_NOW
                </>
              )}
            </Button>
            {selectedStrategy.is_active && (
              <span className="text-xs text-[#006600] font-mono">
                {">"} Auto-executing every {selectedStrategy.execution_interval || 5} minute{(selectedStrategy.execution_interval || 5) !== 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Active Trades */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="text-xs text-[#006600] font-mono uppercase">ACTIVE_TRADES</div>
              <span className="text-[10px] text-[#006600] font-mono">(DCA Avg Entry)</span>
            </div>
            <div className="max-h-[300px] overflow-y-auto space-y-2">
              {!tradingState || !tradingState.balances || tradingState.balances.filter(b => b.token_symbol !== "USDC" && b.balance > 0).length === 0 ? (
                <div className="p-6 text-center bg-[#0a0a0a] border border-[#1a1a1a]">
                  <p className="text-[#006600] font-mono text-xs">
                    {">"} No active positions. All capital is in USDC.
                  </p>
                </div>
              ) : (
                tradingState.balances
                  .filter(balance => balance.token_symbol !== "USDC" && balance.balance > 0)
                  .map((balance, index) => {
                    const entryPrice = balance.entry_price;
                    const currentPrice = balance.current_price || 0;
                    const unrealizedPnl = balance.unrealized_pnl || 0;
                    const pnlPercent = entryPrice && entryPrice > 0 
                      ? ((currentPrice - entryPrice) / entryPrice) * 100 
                      : 0;
                    
                    return (
                      <div
                        key={`${balance.token_symbol}-${index}`}
                        className="p-4 bg-[#0a0a0a] border border-[#1a1a1a] hover:border-[#00ff00]/50 transition-all"
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="px-2 py-0.5 text-[10px] font-mono border bg-[#00ff00]/20 text-[#00ff00] border-[#00ff00]">
                                {balance.token_symbol}
                              </span>
                              <span className="text-xs text-[#006600] font-mono">
                                Balance: {balance.balance.toFixed(6)}
                              </span>
                            </div>
                            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                              <div>
                                <span className="text-[#006600]">Avg Entry (DCA):</span>
                                <span className="text-[#00ff00] ml-2">
                                  ${entryPrice ? entryPrice.toFixed(6) : "N/A"}
                                </span>
                              </div>
                              <div>
                                <span className="text-[#006600]">Current Price:</span>
                                <span className="text-[#00ff00] ml-2">
                                  ${currentPrice > 0 ? currentPrice.toFixed(6) : "N/A"}
                                </span>
                              </div>
                              <div>
                                <span className="text-[#006600]">Position Value:</span>
                                <span className="text-[#00ff00] ml-2">
                                  ${balance.usd_value.toFixed(2)}
                                </span>
                              </div>
                              <div>
                                <span className="text-[#006600]">Unrealized P&L:</span>
                                <span className={`ml-2 ${
                                  unrealizedPnl >= 0 ? "text-[#00ff00]" : "text-[#ff0000]"
                                }`}>
                                  {unrealizedPnl >= 0 ? "+" : ""}${unrealizedPnl.toFixed(2)} ({pnlPercent >= 0 ? "+" : ""}{pnlPercent.toFixed(2)}%)
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })
              )}
            </div>
          </div>

          {/* Trade History */}
          <div className="space-y-3">
            <div className="text-xs text-[#006600] font-mono uppercase">TRADE_HISTORY</div>
            <div className="max-h-[300px] overflow-y-auto space-y-2">
              {executions.filter(e => e.trade_executed).length === 0 ? (
                <div className="p-6 text-center bg-[#0a0a0a] border border-[#1a1a1a]">
                  <p className="text-[#006600] font-mono text-xs">
                    {">"} No trades executed yet.
                  </p>
                </div>
              ) : (
                executions
                  .filter(e => e.trade_executed)
                  .map((trade) => (
                    <div
                      key={`trade-${trade.id}`}
                      className="p-4 bg-[#0a0a0a] border border-[#1a1a1a] hover:border-[#00ff00]/50 transition-all"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 text-[10px] font-mono border ${
                            trade.side === "buy"
                              ? "bg-[#00ff00]/20 text-[#00ff00] border-[#00ff00]"
                              : "bg-[#ff0000]/20 text-[#ff0000] border-[#ff0000]"
                          }`}>
                            {trade.side?.toUpperCase()}
                          </span>
                          <span className="text-xs text-[#00ff00] font-mono">
                            {trade.symbol}
                          </span>
                        </div>
                        <span className="text-[10px] text-[#006600] font-mono">
                          {new Date(trade.execution_timestamp).toLocaleString()}
                        </span>
                      </div>
                      <div className="grid grid-cols-3 gap-3 text-xs font-mono mt-2">
                        <div>
                          <span className="text-[#006600]">Amount In:</span>
                          <span className="text-[#00ff00] ml-2">
                            {trade.side === "buy" 
                              ? `$${trade.amount_in?.toFixed(2)}` 
                              : `${trade.amount_in?.toFixed(6)} ${trade.symbol?.split('-')[0]}`}
                          </span>
                        </div>
                        <div>
                          <span className="text-[#006600]">Amount Out:</span>
                          <span className="text-[#00ff00] ml-2">
                            {trade.side === "buy" 
                              ? `${trade.amount_out?.toFixed(6)} ${trade.symbol?.split('-')[0]}`
                              : `$${trade.amount_out?.toFixed(2)}`}
                          </span>
                        </div>
                        <div>
                          <span className="text-[#006600]">Price:</span>
                          <span className="text-[#00ff00] ml-2">
                            ${trade.price?.toFixed(6)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))
              )}
            </div>
          </div>

          {/* Execution Logs */}
          <div className="space-y-3">
            <div className="text-xs text-[#006600] font-mono uppercase">EXECUTION_LOGS</div>
            <div className="max-h-[400px] overflow-y-auto space-y-2">
              {executions.length === 0 ? (
                <div className="p-6 text-center bg-[#0a0a0a] border border-[#1a1a1a]">
                  <p className="text-[#006600] font-mono text-xs">
                    {">"} No executions yet. Click EXECUTE_NOW to run the strategy.
                  </p>
                </div>
              ) : (
                executions.map((execution) => (
                  <div
                    key={execution.id}
                    className="p-4 bg-[#0a0a0a] border border-[#1a1a1a] hover:border-[#00ff00]/50 transition-all"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 text-[10px] font-mono border ${
                          execution.decision === "BUY"
                            ? "bg-[#00ff00]/20 text-[#00ff00] border-[#00ff00]"
                            : execution.decision === "SELL"
                            ? "bg-[#ff0000]/20 text-[#ff0000] border-[#ff0000]"
                            : "bg-[#666]/20 text-[#666] border-[#666]"
                        }`}>
                          {execution.decision}
                        </span>
                        <span className="text-xs text-[#006600] font-mono">
                          Confidence: {(execution.confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                      <span className="text-[10px] text-[#006600] font-mono">
                        {new Date(execution.execution_timestamp).toLocaleString()}
                      </span>
                    </div>
                    {execution.reasoning && (
                      <p className="text-xs text-[#006600] font-mono mt-2 leading-relaxed">
                        {execution.reasoning}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

