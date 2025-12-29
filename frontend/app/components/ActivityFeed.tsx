"use client";

import { Activity, TrendingUp, TrendingDown, RefreshCw, BarChart3, Brain } from "lucide-react";

const activities = [
  {
    id: 1,
    type: "trade",
    action: "BUY",
    pair: "WETH/USDC",
    time: "2m ago",
    icon: TrendingUp,
    isPositive: true,
  },
  {
    id: 2,
    type: "analysis",
    action: "ANALYSIS",
    pair: "MOVE/USDC",
    time: "5m ago",
    icon: Brain,
    isPositive: null,
  },
  {
    id: 3,
    type: "price",
    action: "PRICE_UPDATE",
    pair: "WETH",
    time: "8m ago",
    icon: RefreshCw,
    isPositive: null,
  },
  {
    id: 4,
    type: "trade",
    action: "SELL",
    pair: "WETH/USDC",
    time: "15m ago",
    icon: TrendingDown,
    isPositive: false,
  },
  {
    id: 5,
    type: "sentiment",
    action: "SENTIMENT",
    pair: "WETH",
    time: "1h ago",
    icon: BarChart3,
    isPositive: null,
  },
];

export function ActivityFeed() {
  return (
    <div className="p-5 bg-[#0f0f0f] border border-[#1a1a1a] font-mono">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-[#00ff00]" />
          <h3 className="text-sm text-[#00ff00] uppercase">{"// Activity Log"}</h3>
        </div>
        <span className="text-[10px] text-[#006600] flex items-center gap-1">
          <span className="w-1.5 h-1.5 bg-[#00ff00] animate-pulse-terminal"></span>
          LIVE
        </span>
      </div>

      <div className="space-y-1">
        {activities.map((activity) => (
          <div
            key={activity.id}
            className="flex items-center gap-3 p-2 hover:bg-[#00ff00]/5 transition-colors cursor-pointer border-l-2 border-transparent hover:border-[#00ff00]"
          >
            <div className={`w-6 h-6 flex items-center justify-center flex-shrink-0 ${
              activity.isPositive === true 
                ? "text-[#00ff00]" 
                : activity.isPositive === false 
                ? "text-[#ff3333]" 
                : "text-[#006600]"
            }`}>
              <activity.icon className="h-3 w-3" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 text-xs">
                <span className={`font-bold ${
                  activity.isPositive === true 
                    ? "text-[#00ff00]" 
                    : activity.isPositive === false 
                    ? "text-[#ff3333]" 
                    : "text-[#00aa00]"
                }`}>
                  [{activity.action}]
                </span>
                <span className="text-[#006600]">{activity.pair}</span>
                <span className="text-[#004400] ml-auto">{activity.time}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <button className="w-full mt-3 py-2 text-xs text-[#006600] hover:text-[#00ff00] transition-colors border border-[#1a1a1a] hover:border-[#00ff00]">
        {">"} view_all --logs
      </button>
    </div>
  );
}
