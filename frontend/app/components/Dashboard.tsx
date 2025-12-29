"use client";

import { useState } from "react";
import { 
  Terminal, 
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
  { id: "overview", label: "./overview", icon: Terminal },
  { id: "agent", label: "./agent", icon: Bot },
  { id: "analytics", label: "./analytics", icon: BarChart3 },
  { id: "history", label: "./history", icon: History },
  { id: "settings", label: "./config", icon: Settings },
];

const quickStats = [
  { label: "trades_today", value: "12", change: "+3", positive: true, icon: Activity },
  { label: "win_rate", value: "83%", change: "+5%", positive: true, icon: TrendingUp },
  { label: "total_pnl", value: "+$243", change: "", positive: true, icon: DollarSign },
  { label: "uptime", value: "2h 34m", change: "", positive: true, icon: Clock },
];

export function Dashboard() {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div className="min-h-screen pt-4 pb-8 scanline">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="mb-8">
          <div className="inline-flex border border-[#1a1a1a] p-1 font-mono">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 text-xs font-medium transition-all ${
                  activeTab === tab.id
                    ? "bg-[#00ff00] text-[#0a0a0a]"
                    : "text-[#006600] hover:text-[#00ff00] hover:bg-[#00ff00]/10"
                }`}
              >
                <tab.icon className="h-3 w-3" />
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {activeTab === "overview" && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {quickStats.map((stat) => (
                <div key={stat.label} className="p-5 bg-[#0f0f0f] border border-[#1a1a1a] hover:border-[#00ff00] transition-all">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-[#006600] font-mono uppercase">{stat.label}</span>
                    <stat.icon className="h-4 w-4 text-[#006600]" />
                  </div>
                  <div className="flex items-end gap-2">
                    <span className="text-2xl font-bold text-[#00ff00] font-mono glow-text-subtle">{stat.value}</span>
                    {stat.change && (
                      <span className="text-sm text-[#00aa00] mb-0.5 font-mono">{stat.change}</span>
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
          <div className="p-12 bg-[#0f0f0f] border border-[#1a1a1a] text-center font-mono">
            <BarChart3 className="h-12 w-12 text-[#006600] mx-auto mb-4" />
            <h3 className="text-lg font-bold text-[#00ff00] mb-2">{"// ANALYTICS MODULE"}</h3>
            <p className="text-[#006600] text-sm max-w-md mx-auto">
              {">"} 70+ technical indicators
              <br />
              {">"} Sentiment timeline
              <br />
              {">"} Performance metrics
              <br />
              <span className="text-[#00aa00]">[STATUS: COMING_SOON]</span>
            </p>
          </div>
        )}

        {activeTab === "history" && (
          <TradeHistory />
        )}

        {activeTab === "settings" && (
          <div className="p-12 bg-[#0f0f0f] border border-[#1a1a1a] text-center font-mono">
            <Settings className="h-12 w-12 text-[#006600] mx-auto mb-4" />
            <h3 className="text-lg font-bold text-[#00ff00] mb-2">{"// CONFIG MODULE"}</h3>
            <p className="text-[#006600] text-sm max-w-md mx-auto">
              {">"} Trading modes configuration
              <br />
              {">"} Risk management rules
              <br />
              {">"} Notification settings
              <br />
              <span className="text-[#00aa00]">[STATUS: COMING_SOON]</span>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
