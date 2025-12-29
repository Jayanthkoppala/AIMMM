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
  DollarSign,
  Clock
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
  { label: "Today's Trades", value: "12", change: "+3", positive: true, icon: Activity },
  { label: "Win Rate", value: "83%", change: "+5%", positive: true, icon: TrendingUp },
  { label: "Total P&L", value: "+$243", change: "", positive: true, icon: DollarSign },
  { label: "Active Since", value: "2h 34m", change: "", positive: true, icon: Clock },
];

export function Dashboard() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="min-h-screen pt-4 pb-8">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="inline-flex bg-[#111317] border border-[#1F1F24] rounded-lg p-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  activeTab === tab.id
                    ? "bg-emerald text-white"
                    : "text-gray-400 hover:text-white"
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
                <div key={stat.label} className="p-5 rounded-xl bg-[#111317] border border-[#1F1F24]">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm text-gray-400">{stat.label}</span>
                    <stat.icon className="h-4 w-4 text-gray-500" />
                  </div>
                  <div className="flex items-end gap-2">
                    <span className="text-2xl font-semibold text-white">{stat.value}</span>
                    {stat.change && (
                      <span className="text-sm text-emerald mb-0.5">{stat.change}</span>
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
          <div className="p-12 rounded-xl bg-[#111317] border border-[#1F1F24] text-center">
            <BarChart3 className="h-12 w-12 text-gray-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">Analytics Coming Soon</h3>
            <p className="text-gray-400 text-sm max-w-md mx-auto">
              Advanced charts with 70+ technical indicators, sentiment timeline, and performance metrics.
            </p>
          </div>
        )}

        {activeTab === "history" && (
          <TradeHistory />
        )}

        {activeTab === "settings" && (
          <div className="p-12 rounded-xl bg-[#111317] border border-[#1F1F24] text-center">
            <Settings className="h-12 w-12 text-gray-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">Settings Coming Soon</h3>
            <p className="text-gray-400 text-sm max-w-md mx-auto">
              Configure trading modes, risk management, notifications, and pool settings.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
