"use client";

import { Activity, TrendingUp, TrendingDown, RefreshCw, BarChart3, Brain } from "lucide-react";

const activities = [
  {
    id: 1,
    type: "trade",
    action: "BUY",
    pair: "WETH/USDC",
    time: "2 mins ago",
    icon: TrendingUp,
    isPositive: true,
  },
  {
    id: 2,
    type: "analysis",
    action: "Analysis Complete",
    pair: "MOVE/USDC",
    time: "5 mins ago",
    icon: Brain,
    isPositive: null,
  },
  {
    id: 3,
    type: "price",
    action: "Price Updated",
    pair: "WETH",
    time: "8 mins ago",
    icon: RefreshCw,
    isPositive: null,
  },
  {
    id: 4,
    type: "trade",
    action: "SELL",
    pair: "WETH/USDC",
    time: "15 mins ago",
    icon: TrendingDown,
    isPositive: false,
  },
  {
    id: 5,
    type: "sentiment",
    action: "Sentiment Refreshed",
    pair: "WETH",
    time: "1 hour ago",
    icon: BarChart3,
    isPositive: null,
  },
];

export function ActivityFeed() {
  return (
    <div className="p-5 rounded-xl bg-[#111317] border border-[#1F1F24]">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-gray-400" />
          <h3 className="font-medium text-white">Activity</h3>
        </div>
        <span className="text-xs text-gray-500">Real-time</span>
      </div>

      <div className="space-y-2">
        {activities.map((activity) => (
          <div
            key={activity.id}
            className="flex items-center gap-3 p-3 rounded-lg bg-[#1A1D23] hover:bg-[#2A2D33] transition-colors cursor-pointer"
          >
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
              activity.isPositive === true 
                ? "bg-emerald/10" 
                : activity.isPositive === false 
                ? "bg-red-500/10" 
                : "bg-gray-500/10"
            }`}>
              <activity.icon className={`h-4 w-4 ${
                activity.isPositive === true 
                  ? "text-emerald" 
                  : activity.isPositive === false 
                  ? "text-red-400" 
                  : "text-gray-400"
              }`} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={`text-sm font-medium ${
                  activity.isPositive === true 
                    ? "text-emerald" 
                    : activity.isPositive === false 
                    ? "text-red-400" 
                    : "text-white"
                }`}>
                  {activity.action}
                </span>
                <span className="text-sm text-gray-400">{activity.pair}</span>
              </div>
              <span className="text-xs text-gray-500">{activity.time}</span>
            </div>
          </div>
        ))}
      </div>

      <button className="w-full mt-4 py-2 text-sm text-gray-400 hover:text-white transition-colors">
        View All Activity
      </button>
    </div>
  );
}
