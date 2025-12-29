"use client";

import { TrendingUp, TrendingDown, BarChart3 } from "lucide-react";

const marketData = {
  pair: "WETH/USDC",
  price: "$2,456.78",
  change: "+2.34%",
  isPositive: true,
  volume: "$12.4K",
  high24h: "$2,512.00",
  low24h: "$2,398.45",
};

const balances = [
  { token: "WETH", amount: "0.5", value: "$1,228.39" },
  { token: "USDC", amount: "1,234.56", value: "$1,234.56" },
  { token: "MOVE", amount: "500.00", value: "$445.00" },
];

export function MarketOverview() {
  return (
    <div className="glass-card rounded-2xl p-5">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="h-5 w-5 text-cyber-blue" />
        <h3 className="font-semibold text-white">Market Overview</h3>
      </div>

      <div className="p-4 rounded-xl bg-cyber-bg/50 mb-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm text-gray-400">{marketData.pair}</span>
          <div className={`flex items-center gap-1 text-sm ${marketData.isPositive ? 'text-cyber-green' : 'text-cyber-red'}`}>
            {marketData.isPositive ? (
              <TrendingUp className="h-4 w-4" />
            ) : (
              <TrendingDown className="h-4 w-4" />
            )}
            {marketData.change}
          </div>
        </div>
        <div className="text-2xl font-bold text-white mb-3">{marketData.price}</div>
        
        <div className="h-16 flex items-end gap-1">
          {[35, 42, 38, 55, 48, 62, 58, 70, 65, 75, 72, 80].map((height, i) => (
            <div
              key={i}
              className="flex-1 bg-gradient-to-t from-cyber-indigo/30 to-cyber-indigo rounded-sm"
              style={{ height: `${height}%` }}
            />
          ))}
        </div>

        <div className="flex justify-between text-xs text-gray-500 mt-3">
          <div>
            <span className="block text-gray-400">24h Volume</span>
            <span className="text-white">{marketData.volume}</span>
          </div>
          <div className="text-right">
            <span className="block text-gray-400">24h High/Low</span>
            <span className="text-white">{marketData.high24h} / {marketData.low24h}</span>
          </div>
        </div>
      </div>

      <div>
        <h4 className="text-sm font-medium text-gray-400 mb-3">Your Balance</h4>
        <div className="space-y-2">
          {balances.map((balance) => (
            <div
              key={balance.token}
              className="flex items-center justify-between p-3 rounded-lg bg-cyber-bg/50"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-cyber-indigo/20 flex items-center justify-center text-xs font-bold text-cyber-indigo">
                  {balance.token.slice(0, 2)}
                </div>
                <div>
                  <span className="text-sm font-medium text-white">{balance.token}</span>
                  <span className="block text-xs text-gray-500">{balance.amount}</span>
                </div>
              </div>
              <span className="text-sm font-mono text-gray-300">{balance.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
