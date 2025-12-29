"use client";

import { TrendingUp, TrendingDown, Database } from "lucide-react";

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
    <div className="p-5 bg-[#0f0f0f] border border-[#1a1a1a] font-mono">
      <div className="flex items-center gap-2 mb-4">
        <Database className="h-4 w-4 text-[#00ff00]" />
        <h3 className="text-sm text-[#00ff00] uppercase">{"// Market Data"}</h3>
      </div>

      <div className="p-4 bg-[#0a0a0a] border border-[#1a1a1a] mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-[#006600]">{marketData.pair}</span>
          <div className={`flex items-center gap-1 text-xs ${marketData.isPositive ? 'text-[#00ff00]' : 'text-[#ff3333]'}`}>
            {marketData.isPositive ? (
              <TrendingUp className="h-3 w-3" />
            ) : (
              <TrendingDown className="h-3 w-3" />
            )}
            {marketData.change}
          </div>
        </div>
        <div className="text-2xl font-bold text-[#00ff00] mb-3 glow-text-subtle">{marketData.price}</div>
        
        <div className="h-10 flex items-end gap-0.5">
          {[35, 42, 38, 55, 48, 62, 58, 70, 65, 75, 72, 80].map((height, i) => (
            <div
              key={i}
              className="flex-1 bg-[#00ff00]/30 border-t border-[#00ff00]"
              style={{ height: `${height}%` }}
            />
          ))}
        </div>

        <div className="flex justify-between text-[10px] mt-3">
          <div>
            <span className="block text-[#004400]">vol_24h</span>
            <span className="text-[#00aa00]">{marketData.volume}</span>
          </div>
          <div className="text-right">
            <span className="block text-[#004400]">range_24h</span>
            <span className="text-[#00aa00]">{marketData.low24h} - {marketData.high24h}</span>
          </div>
        </div>
      </div>

      <div>
        <h4 className="text-xs text-[#006600] mb-3 uppercase">{"// Wallet Balances"}</h4>
        <div className="space-y-1">
          {balances.map((balance) => (
            <div
              key={balance.token}
              className="flex items-center justify-between p-2 hover:bg-[#00ff00]/5 transition-colors"
            >
              <div className="flex items-center gap-3">
                <div className="w-6 h-6 border border-[#00ff00] flex items-center justify-center text-[10px] font-bold text-[#00ff00]">
                  {balance.token.slice(0, 2)}
                </div>
                <div>
                  <span className="text-xs text-[#00ff00]">{balance.token}</span>
                  <span className="block text-[10px] text-[#006600]">{balance.amount}</span>
                </div>
              </div>
              <span className="text-xs text-[#00aa00]">{balance.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
