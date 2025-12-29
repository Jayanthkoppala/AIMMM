"use client";

import { useState } from "react";
import { useAgent } from "@/app/hooks/use-agent";
import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { usePrivyWallet } from "@/app/hooks/use-privy-wallet";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { 
  Play, 
  TrendingUp, 
  TrendingDown, 
  Minus,
  DollarSign, 
  Brain, 
  CheckCircle2, 
  ExternalLink,
  Loader2,
  BarChart3,
  Zap,
  Sparkles,
  ArrowRight
} from "lucide-react";

const DEFAULT_TOKEN_A = process.env.NEXT_PUBLIC_TOKEN_A_ADDRESS || "0x...";
const DEFAULT_TOKEN_B = process.env.NEXT_PUBLIC_TOKEN_B_ADDRESS || "0x...";
const DEFAULT_POOL_ADDRESS = process.env.NEXT_PUBLIC_POOL_ADDRESS || "0xbcbf55e1004687d412f05856ef7c17dcaacc1be632ba2d67b71073d25b425c3b";

export function AgentDashboard() {
  const { account, connected } = useWallet();
  const { authenticated, getAccessToken } = usePrivyWallet();
  const { runAgent, isLoading, result } = useAgent();
  
  const [mode, setMode] = useState<"analysis" | "trade" | "autonomous">("analysis");
  const [tokenA, setTokenA] = useState(DEFAULT_TOKEN_A);
  const [tokenB, setTokenB] = useState(DEFAULT_TOKEN_B);
  const [poolAddress, setPoolAddress] = useState(DEFAULT_POOL_ADDRESS);

  const handleRunAgent = async () => {
    if (mode === "autonomous") {
      if (!authenticated) {
        alert("Please login with Privy to enable autonomous trading");
        return;
      }
    } else {
      if (!connected) {
        alert("Please connect your wallet first");
        return;
      }
    }

    try {
      const accessToken = mode === "autonomous" ? await getAccessToken() : undefined;
      await runAgent({
        mode,
        token_pair: {
          token_a: tokenA,
          token_b: tokenB,
        },
        pool_address: poolAddress || undefined,
        privy_access_token: accessToken ?? undefined,
      });
    } catch (error) {
      console.error("Agent execution failed:", error);
    }
  };

  return (
    <div className="space-y-6">
      <div className="glass-card rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyber-indigo to-cyber-purple flex items-center justify-center">
            <Brain className="h-5 w-5 text-white" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">AI Agent Control</h2>
            <p className="text-sm text-gray-400">Configure and execute trading strategies</p>
          </div>
        </div>

        <div className="space-y-6">
          <div className="space-y-3">
            <Label className="text-sm font-medium text-gray-300">Execution Mode</Label>
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => setMode("analysis")}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl transition-all ${
                  mode === "analysis"
                    ? "bg-cyber-indigo/20 border-2 border-cyber-indigo text-white"
                    : "bg-cyber-bg/50 border border-cyber-card hover:border-cyber-indigo/50 text-gray-400"
                }`}
              >
                <BarChart3 className="h-5 w-5" />
                <span className="text-sm font-medium">Analysis</span>
              </button>
              <button
                onClick={() => setMode("trade")}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl transition-all ${
                  mode === "trade"
                    ? "bg-cyber-indigo/20 border-2 border-cyber-indigo text-white"
                    : "bg-cyber-bg/50 border border-cyber-card hover:border-cyber-indigo/50 text-gray-400"
                }`}
              >
                <Zap className="h-5 w-5" />
                <span className="text-sm font-medium">Trade</span>
              </button>
              <button
                onClick={() => setMode("autonomous")}
                className={`flex flex-col items-center gap-2 p-4 rounded-xl transition-all ${
                  mode === "autonomous"
                    ? "bg-cyber-purple/20 border-2 border-cyber-purple text-white"
                    : "bg-cyber-bg/50 border border-cyber-card hover:border-cyber-purple/50 text-gray-400"
                }`}
              >
                <Sparkles className="h-5 w-5" />
                <span className="text-sm font-medium">Auto</span>
              </button>
            </div>
            
            {mode === "autonomous" && (
              <div className="p-4 rounded-xl bg-cyber-purple/10 border border-cyber-purple/30">
                <div className="flex items-start gap-3">
                  <Sparkles className="h-5 w-5 text-cyber-purple mt-0.5" />
                  <div>
                    <p className="font-medium text-cyber-purple">Autonomous Trading</p>
                    <p className="text-sm text-gray-400 mt-1">
                      AI executes trades automatically. Powered by Privy embedded wallets.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="h-px bg-gradient-to-r from-transparent via-cyber-indigo/30 to-transparent" />

          <div className="space-y-4">
            <Label className="text-sm font-medium text-gray-300">Token Pair</Label>
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <Input
                  value={tokenA}
                  onChange={(e) => setTokenA(e.target.value)}
                  placeholder="Token A Address"
                  className="font-mono text-sm bg-cyber-bg border-cyber-card focus:border-cyber-indigo text-white placeholder:text-gray-600"
                />
              </div>
              <ArrowRight className="h-5 w-5 text-cyber-indigo flex-shrink-0" />
              <div className="flex-1">
                <Input
                  value={tokenB}
                  onChange={(e) => setTokenB(e.target.value)}
                  placeholder="Token B Address"
                  className="font-mono text-sm bg-cyber-bg border-cyber-card focus:border-cyber-indigo text-white placeholder:text-gray-600"
                />
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <Label className="text-sm font-medium text-gray-300">Pool Address</Label>
            <Input
              value={poolAddress}
              onChange={(e) => setPoolAddress(e.target.value)}
              placeholder="Enter pool address"
              className="font-mono text-sm bg-cyber-bg border-cyber-card focus:border-cyber-indigo text-white placeholder:text-gray-600"
            />
          </div>

          <div className="h-px bg-gradient-to-r from-transparent via-cyber-indigo/30 to-transparent" />

          <Button
            onClick={handleRunAgent}
            disabled={isLoading || (mode !== "autonomous" && !connected) || (mode === "autonomous" && !authenticated)}
            className={`w-full h-14 text-lg font-semibold border-0 ${
              isLoading 
                ? "bg-cyber-card text-gray-400" 
                : "cyber-button text-white animate-pulse-glow"
            }`}
          >
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Play className="h-5 w-5 mr-2" />
                Run Agent
              </>
            )}
          </Button>
        </div>
      </div>

      {result && (
        <div className="glass-card rounded-2xl p-6 animate-in slide-in-from-bottom-4 duration-500">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-cyber-green/20 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5 text-cyber-green" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">Execution Results</h2>
              <p className="text-sm text-gray-400">Analysis complete</p>
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <DollarSign className="h-4 w-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-300">Oracle Prices</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-4 rounded-xl bg-cyber-bg/50 border border-cyber-card">
                  <span className="text-xs text-gray-500 block mb-1">Token A</span>
                  <span className="text-xl font-bold font-mono text-white">
                    ${result.oracle_price.token_a.toFixed(4)}
                  </span>
                </div>
                <div className="p-4 rounded-xl bg-cyber-bg/50 border border-cyber-card">
                  <span className="text-xs text-gray-500 block mb-1">Token B</span>
                  <span className="text-xl font-bold font-mono text-white">
                    ${result.oracle_price.token_b.toFixed(4)}
                  </span>
                </div>
              </div>
            </div>

            <div className="h-px bg-gradient-to-r from-transparent via-cyber-indigo/30 to-transparent" />

            <div>
              <div className="flex items-center gap-2 mb-3">
                <Brain className="h-4 w-4 text-cyber-indigo" />
                <span className="text-sm font-medium text-gray-300">AI Decision</span>
              </div>
              
              <div className="p-4 rounded-xl bg-cyber-bg/50 border border-cyber-card mb-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Recommended Action</span>
                  <div className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold ${
                    result.llm_decision.action === "BUY" 
                      ? "action-badge-buy" 
                      : result.llm_decision.action === "SELL"
                      ? "action-badge-sell"
                      : "action-badge-hold"
                  }`}>
                    {result.llm_decision.action === "BUY" && <TrendingUp className="h-4 w-4" />}
                    {result.llm_decision.action === "SELL" && <TrendingDown className="h-4 w-4" />}
                    {result.llm_decision.action === "HOLD" && <Minus className="h-4 w-4" />}
                    {result.llm_decision.action}
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Confidence Level</span>
                  <span className="font-semibold text-white">
                    {(result.llm_decision.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="confidence-bar">
                  <div
                    className="confidence-fill"
                    style={{ width: `${result.llm_decision.confidence * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {result.executed && result.tx_hash && (
              <>
                <div className="h-px bg-gradient-to-r from-transparent via-cyber-green/30 to-transparent" />
                
                <div className="p-4 rounded-xl bg-cyber-green/10 border border-cyber-green/30">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-cyber-green" />
                    <div className="flex-1">
                      <span className="text-sm text-gray-400 block mb-1">Trade Executed</span>
                      <a
                        href={`https://explorer.movementnetwork.xyz/txn/${result.tx_hash}?network=mainnet`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-cyber-indigo hover:text-cyber-purple font-mono text-sm flex items-center gap-1 transition-colors"
                      >
                        {result.tx_hash.slice(0, 16)}...{result.tx_hash.slice(-8)}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
