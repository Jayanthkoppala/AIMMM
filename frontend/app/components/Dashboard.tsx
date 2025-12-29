"use client";

import { useState } from "react";
import { 
  LayoutDashboard, 
  Bot, 
  BarChart3, 
  History, 
  Settings,
  Activity,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Clock,
  Zap
} from "lucide-react";
import { AgentDashboard } from "./AgentDashboard";
import { TradeHistory } from "./TradeHistory";
import { ActivityFeed } from "./ActivityFeed";
import { MarketOverview } from "./MarketOverview";

const tabs = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "agent", label: "Agent", icon: Bot },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
  { id: "history", label: "History", icon: History },
  { id: "settings", label: "Settings", icon: Settings },
];

const quickStats = [
  { label: "Today's Trades", value: "12", change: "+3", icon: Activity, color: "cyber-indigo" },
  { label: "Win Rate", value: "83%", change: "+5%", icon: TrendingUp, color: "cyber-green" },
  { label: "Total P&L", value: "+$243", change: "", icon: DollarSign, color: "cyber-green" },
  { label: "Active Since", value: "2h 34m", change: "", icon: Clock, color: "cyber-purple" },
];

export function Dashboard() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="min-h-screen pt-4 pb-8">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="glass-card rounded-xl p-1 inline-flex">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? "bg-cyber-indigo text-white shadow-glow"
                    : "text-gray-400 hover:text-white hover:bg-cyber-card/50"
                }`}
              >
                <tab.icon className="h-4 w-4" />
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {quickStats.map((stat) => (
                <div key={stat.label} className="stat-card">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-gray-400">{stat.label}</span>
                    <stat.icon className={`h-4 w-4 text-${stat.color}`} />
                  </div>
                  <div className="flex items-end gap-2">
                    <span className="text-2xl font-bold text-white">{stat.value}</span>
                    {stat.change && (
                      <span className="text-sm text-cyber-green mb-1">{stat.change}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>

            <div className="grid gap-6 lg:grid-cols-5">
              <div className="lg:col-span-3">
                <AgentDashboard />
              </div>
              <div className="lg:col-span-2 space-y-6">
                <ActivityFeed />
                <MarketOverview />
              </div>
            </div>
          </div>
        )}

        {activeTab === "agent" && (
          <div className="max-w-4xl">
            <AgentDashboard />
          </div>
        )}

        {activeTab === "analytics" && (
          <div className="glass-card rounded-2xl p-8 text-center">
            <BarChart3 className="h-16 w-16 text-cyber-indigo mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Analytics Coming Soon</h3>
            <p className="text-gray-400">
              Advanced charts with 70+ technical indicators, sentiment timeline, and more.
            </p>
          </div>
        )}

        {activeTab === "history" && (
          <TradeHistory />
        )}

        {activeTab === "settings" && (
          <div className="glass-card rounded-2xl p-8 text-center">
            <Settings className="h-16 w-16 text-cyber-indigo mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Settings Coming Soon</h3>
            <p className="text-gray-400">
              Configure trading modes, risk management, and pool settings.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
