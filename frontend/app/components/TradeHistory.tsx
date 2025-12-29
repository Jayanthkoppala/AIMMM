"use client";

import { useState, useEffect } from "react";
import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { Button } from "./ui/button";
import { getExplorerUrl } from "@/app/lib/aptos";
import { 
  History, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Clock, 
  DollarSign, 
  ExternalLink,
  Loader2,
  Inbox,
  Filter,
  Download
} from "lucide-react";

interface TradeHistoryItem {
  id: string;
  mode: string;
  token_a_address: string;
  token_b_address: string;
  llm_action: string;
  llm_confidence: number;
  executed: boolean;
  tx_hash: string | null;
  execution_cost: number;
  created_at: string;
}

const demoTrades = [
  {
    id: "1",
    time: "2:34 PM",
    pair: "WETH/USDC",
    action: "BUY",
    price: "$2,451",
    sentiment: "+0.75",
    sentimentEmoji: "bullish",
    pnl: "+$12",
    pnlPositive: true,
  },
  {
    id: "2",
    time: "1:22 PM",
    pair: "WETH/USDC",
    action: "SELL",
    price: "$2,439",
    sentiment: "+0.12",
    sentimentEmoji: "neutral",
    pnl: "-$8",
    pnlPositive: false,
  },
  {
    id: "3",
    time: "12:15 PM",
    pair: "MOVE/USDC",
    action: "HOLD",
    price: "$0.89",
    sentiment: "+0.82",
    sentimentEmoji: "bullish",
    pnl: "$0",
    pnlPositive: true,
  },
  {
    id: "4",
    time: "11:45 AM",
    pair: "WETH/USDC",
    action: "BUY",
    price: "$2,423",
    sentiment: "+0.65",
    sentimentEmoji: "bullish",
    pnl: "+$28",
    pnlPositive: true,
  },
  {
    id: "5",
    time: "10:30 AM",
    pair: "MOVE/USDC",
    action: "SELL",
    price: "$0.92",
    sentiment: "-0.23",
    sentimentEmoji: "bearish",
    pnl: "+$15",
    pnlPositive: true,
  },
];

const metrics = {
  totalTrades: 156,
  winRate: "83%",
  totalPnl: "+$1,234",
  bestTrade: "+$89",
  worstTrade: "-$23",
  avgTrade: "+$7.91",
};

export function TradeHistory() {
  const { account } = useWallet();
  const [trades, setTrades] = useState<TradeHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState("All");

  useEffect(() => {
    setLoading(false);
  }, [account]);

  if (loading) {
    return (
      <div className="glass-card rounded-2xl p-8">
        <div className="flex flex-col items-center justify-center gap-3 text-gray-400">
          <Loader2 className="h-6 w-6 animate-spin text-cyber-indigo" />
          <div>Loading trade history...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="glass-card rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyber-blue/20 flex items-center justify-center">
            <History className="h-5 w-5 text-cyber-blue" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Trade History</h2>
            <p className="text-sm text-gray-400">View your past trading activity</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="bg-cyber-bg border-cyber-card hover:border-cyber-indigo text-gray-400 hover:text-white">
            <Filter className="h-4 w-4 mr-1" />
            Filter
          </Button>
          <Button variant="outline" size="sm" className="bg-cyber-bg border-cyber-card hover:border-cyber-indigo text-gray-400 hover:text-white">
            <Download className="h-4 w-4 mr-1" />
            Export
          </Button>
        </div>
      </div>

      <div className="flex gap-2 mb-6">
        {["All", "BUY", "SELL", "HOLD"].map((filter) => (
          <button
            key={filter}
            onClick={() => setActiveFilter(filter)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              activeFilter === filter
                ? "bg-cyber-indigo text-white"
                : "bg-cyber-bg/50 text-gray-400 hover:text-white hover:bg-cyber-card/50"
            }`}
          >
            {filter}
          </button>
        ))}
      </div>

      {trades.length === 0 ? (
        <div className="py-12">
          <div className="flex flex-col items-center justify-center gap-4 text-center">
            <div className="w-16 h-16 rounded-full bg-cyber-card flex items-center justify-center">
              <Inbox className="h-8 w-8 text-gray-500" />
            </div>
            <div className="space-y-1">
              <div className="font-medium text-white">No trades yet</div>
              <div className="text-sm text-gray-400">
                Execute your first agent run to see history here
              </div>
            </div>
          </div>

          <div className="mt-8 p-4 rounded-xl bg-cyber-bg/50 border border-cyber-card">
            <h4 className="text-sm font-medium text-gray-400 mb-3">Demo Data Preview</h4>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b border-cyber-card">
                    <th className="pb-3 font-medium">Time</th>
                    <th className="pb-3 font-medium">Pair</th>
                    <th className="pb-3 font-medium">Action</th>
                    <th className="pb-3 font-medium">Price</th>
                    <th className="pb-3 font-medium">Sentiment</th>
                    <th className="pb-3 font-medium text-right">P&L</th>
                  </tr>
                </thead>
                <tbody className="data-table">
                  {demoTrades.slice(0, 3).map((trade) => (
                    <tr key={trade.id} className="border-b border-cyber-card/50 opacity-60">
                      <td className="py-3 text-sm text-gray-400">{trade.time}</td>
                      <td className="py-3 text-sm font-medium text-white">{trade.pair}</td>
                      <td className="py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold ${
                          trade.action === "BUY" 
                            ? "action-badge-buy" 
                            : trade.action === "SELL"
                            ? "action-badge-sell"
                            : "action-badge-hold"
                        }`}>
                          {trade.action === "BUY" && <TrendingUp className="h-3 w-3" />}
                          {trade.action === "SELL" && <TrendingDown className="h-3 w-3" />}
                          {trade.action === "HOLD" && <Minus className="h-3 w-3" />}
                          {trade.action}
                        </span>
                      </td>
                      <td className="py-3 text-sm font-mono text-gray-300">{trade.price}</td>
                      <td className="py-3">
                        <span className={`text-sm ${
                          trade.sentimentEmoji === "bullish" 
                            ? "text-cyber-green" 
                            : trade.sentimentEmoji === "bearish"
                            ? "text-cyber-red"
                            : "text-cyber-amber"
                        }`}>
                          {trade.sentimentEmoji === "bullish" ? "😊" : trade.sentimentEmoji === "bearish" ? "😟" : "😐"} {trade.sentiment}
                        </span>
                      </td>
                      <td className={`py-3 text-sm font-semibold text-right ${
                        trade.pnlPositive ? "text-cyber-green" : "text-cyber-red"
                      }`}>
                        {trade.pnl}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-xs text-gray-500 border-b border-cyber-card">
                  <th className="pb-3 font-medium">Time</th>
                  <th className="pb-3 font-medium">Mode</th>
                  <th className="pb-3 font-medium">Action</th>
                  <th className="pb-3 font-medium">Confidence</th>
                  <th className="pb-3 font-medium">Cost</th>
                  <th className="pb-3 font-medium text-right">TX</th>
                </tr>
              </thead>
              <tbody className="data-table">
                {trades.map((trade) => (
                  <tr key={trade.id} className="border-b border-cyber-card/50">
                    <td className="py-3 text-sm text-gray-400">
                      <div className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(trade.created_at).toLocaleTimeString()}
                      </div>
                    </td>
                    <td className="py-3">
                      <span className="px-2 py-1 rounded text-xs font-medium bg-cyber-card text-gray-300">
                        {trade.mode}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-semibold ${
                        trade.llm_action === "BUY" 
                          ? "action-badge-buy" 
                          : trade.llm_action === "SELL"
                          ? "action-badge-sell"
                          : "action-badge-hold"
                      }`}>
                        {trade.llm_action === "BUY" && <TrendingUp className="h-3 w-3" />}
                        {trade.llm_action === "SELL" && <TrendingDown className="h-3 w-3" />}
                        {trade.llm_action}
                      </span>
                    </td>
                    <td className="py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-cyber-card rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-cyber-indigo to-cyber-purple rounded-full"
                            style={{ width: `${trade.llm_confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-400">
                          {(trade.llm_confidence * 100).toFixed(0)}%
                        </span>
                      </div>
                    </td>
                    <td className="py-3">
                      <div className="flex items-center gap-1 text-sm font-mono text-gray-300">
                        <DollarSign className="h-3 w-3 text-gray-500" />
                        {trade.execution_cost.toFixed(4)}
                      </div>
                    </td>
                    <td className="py-3 text-right">
                      {trade.executed && trade.tx_hash ? (
                        <a
                          href={getExplorerUrl(trade.tx_hash)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-cyber-indigo hover:text-cyber-purple transition-colors"
                        >
                          <span className="text-xs font-mono">
                            {trade.tx_hash.slice(0, 6)}...
                          </span>
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      ) : (
                        <span className="text-xs text-gray-500">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-6 p-4 rounded-xl bg-cyber-bg/50 border border-cyber-card">
            <h4 className="text-sm font-medium text-gray-400 mb-3">Performance Metrics</h4>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-4 text-center">
              <div>
                <span className="text-lg font-bold text-white">{metrics.totalTrades}</span>
                <span className="block text-xs text-gray-500">Total Trades</span>
              </div>
              <div>
                <span className="text-lg font-bold text-cyber-green">{metrics.winRate}</span>
                <span className="block text-xs text-gray-500">Win Rate</span>
              </div>
              <div>
                <span className="text-lg font-bold text-cyber-green">{metrics.totalPnl}</span>
                <span className="block text-xs text-gray-500">Total P&L</span>
              </div>
              <div>
                <span className="text-lg font-bold text-cyber-green">{metrics.bestTrade}</span>
                <span className="block text-xs text-gray-500">Best Trade</span>
              </div>
              <div>
                <span className="text-lg font-bold text-cyber-red">{metrics.worstTrade}</span>
                <span className="block text-xs text-gray-500">Worst Trade</span>
              </div>
              <div>
                <span className="text-lg font-bold text-white">{metrics.avgTrade}</span>
                <span className="block text-xs text-gray-500">Avg Trade</span>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
