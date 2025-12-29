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
    color: "cyber-green",
  },
  {
    id: 2,
    type: "analysis",
    action: "Analysis Complete",
    pair: "MOVE/USDC",
    time: "5 mins ago",
    icon: Brain,
    color: "cyber-purple",
  },
  {
    id: 3,
    type: "price",
    action: "Price Updated",
    pair: "WETH",
    time: "8 mins ago",
    icon: RefreshCw,
    color: "cyber-blue",
  },
  {
    id: 4,
    type: "trade",
    action: "SELL",
    pair: "WETH/USDC",
    time: "15 mins ago",
    icon: TrendingDown,
    color: "cyber-red",
  },
  {
    id: 5,
    type: "sentiment",
    action: "Sentiment Refreshed",
    pair: "WETH",
    time: "1 hour ago",
    icon: BarChart3,
    color: "cyber-indigo",
  },
];

export function ActivityFeed() {
  return (
    <div className="glass-card rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="h-5 w-5 text-cyber-indigo" />
          <h3 className="font-semibold text-white">Activity Feed</h3>
        </div>
        <span className="text-xs text-gray-500">Real-time</span>
      </div>

      <div className="space-y-3">
        {activities.map((activity) => (
          <div
            key={activity.id}
            className="flex items-center gap-3 p-3 rounded-xl bg-cyber-bg/50 hover:bg-cyber-card/50 transition-colors cursor-pointer"
          >
            <div className={`w-8 h-8 rounded-lg bg-${activity.color}/20 flex items-center justify-center flex-shrink-0`}>
              <activity.icon className={`h-4 w-4 text-${activity.color}`} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className={`text-sm font-medium text-${activity.color}`}>
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
