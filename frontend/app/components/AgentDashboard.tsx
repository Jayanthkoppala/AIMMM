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
      <div className="p-6 rounded-xl bg-[#111317] border border-[#1F1F24]">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-emerald/10 flex items-center justify-center">
            <Brain className="h-5 w-5 text-emerald" />
          </div>
          <div>
            <h2 className="text-lg font-medium text-white">AI Agent Control</h2>
            <p className="text-sm text-gray-400">Configure and execute trading strategies</p>
          </div>
        </div>

        <div className="space-y-6">
          <div className="space-y-3">
            <Label className="text-sm font-medium text-gray-300">Execution Mode</Label>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={() => setMode("analysis")}
                className={`flex flex-col items-center gap-2 p-4 rounded-lg transition-all ${
                  mode === "analysis"
                    ? "bg-emerald/10 border border-emerald text-white"
                    : "bg-[#1A1D23] border border-[#2A2D33] hover:border-gray-500 text-gray-400"
                }`}
              >
                <BarChart3 className="h-5 w-5" />
                <span className="text-sm font-medium">Analysis</span>
              </button>
              <button
                onClick={() => setMode("trade")}
                className={`flex flex-col items-center gap-2 p-4 rounded-lg transition-all ${
                  mode === "trade"
                    ? "bg-emerald/10 border border-emerald text-white"
                    : "bg-[#1A1D23] border border-[#2A2D33] hover:border-gray-500 text-gray-400"
                }`}
              >
                <Zap className="h-5 w-5" />
                <span className="text-sm font-medium">Trade</span>
              </button>
              <button
                onClick={() => setMode("autonomous")}
                className={`flex flex-col items-center gap-2 p-4 rounded-lg transition-all ${
                  mode === "autonomous"
                    ? "bg-emerald/10 border border-emerald text-white"
                    : "bg-[#1A1D23] border border-[#2A2D33] hover:border-gray-500 text-gray-400"
                }`}
              >
                <Sparkles className="h-5 w-5" />
                <span className="text-sm font-medium">Auto</span>
              </button>
            </div>
            
            {mode === "autonomous" && (
              <div className="p-4 rounded-lg bg-emerald/5 border border-emerald/20">
                <div className="flex items-start gap-3">
                  <Sparkles className="h-5 w-5 text-emerald mt-0.5" />
                  <div>
                    <p className="font-medium text-emerald text-sm">Autonomous Trading</p>
                    <p className="text-sm text-gray-400 mt-1">
                      AI executes trades automatically using Privy embedded wallets.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="h-px bg-[#1F1F24]" />

          <div className="space-y-4">
            <Label className="text-sm font-medium text-gray-300">Token Pair</Label>
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <Input
                  value={tokenA}
                  onChange={(e) => setTokenA(e.target.value)}
                  placeholder="Token A Address"
                  className="font-mono text-sm bg-[#1A1D23] border-[#2A2D33] focus:border-emerald text-white placeholder:text-gray-600"
                />
              </div>
              <ArrowRight className="h-5 w-5 text-gray-500 flex-shrink-0" />
              <div className="flex-1">
                <Input
                  value={tokenB}
                  onChange={(e) => setTokenB(e.target.value)}
                  placeholder="Token B Address"
                  className="font-mono text-sm bg-[#1A1D23] border-[#2A2D33] focus:border-emerald text-white placeholder:text-gray-600"
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
              className="font-mono text-sm bg-[#1A1D23] border-[#2A2D33] focus:border-emerald text-white placeholder:text-gray-600"
            />
          </div>

          <div className="h-px bg-[#1F1F24]" />

          <Button
            onClick={handleRunAgent}
            disabled={isLoading || (mode !== "autonomous" && !connected) || (mode === "autonomous" && !authenticated)}
            className={`w-full h-12 text-base font-medium border-0 ${
              isLoading 
                ? "bg-[#2A2D33] text-gray-400" 
                : "bg-emerald hover:bg-emerald-dark text-white"
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
        <div className="p-6 rounded-xl bg-[#111317] border border-[#1F1F24] animate-fade-in">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-emerald/10 flex items-center justify-center">
              <CheckCircle2 className="h-5 w-5 text-emerald" />
            </div>
            <div>
              <h2 className="text-lg font-medium text-white">Results</h2>
              <p className="text-sm text-gray-400">Analysis complete</p>
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <DollarSign className="h-4 w-4 text-gray-500" />
                <span className="text-sm font-medium text-gray-300">Oracle Prices</span>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-4 rounded-lg bg-[#1A1D23] border border-[#2A2D33]">
                  <span className="text-xs text-gray-500 block mb-1">Token A</span>
                  <span className="text-xl font-semibold font-mono text-white">
                    ${result.oracle_price.token_a.toFixed(4)}
                  </span>
                </div>
                <div className="p-4 rounded-lg bg-[#1A1D23] border border-[#2A2D33]">
                  <span className="text-xs text-gray-500 block mb-1">Token B</span>
                  <span className="text-xl font-semibold font-mono text-white">
                    ${result.oracle_price.token_b.toFixed(4)}
                  </span>
                </div>
              </div>
            </div>

            <div className="h-px bg-[#1F1F24]" />

            <div>
              <div className="flex items-center gap-2 mb-3">
                <Brain className="h-4 w-4 text-emerald" />
                <span className="text-sm font-medium text-gray-300">AI Decision</span>
              </div>
              
              <div className="p-4 rounded-lg bg-[#1A1D23] border border-[#2A2D33] mb-4">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400 text-sm">Recommended Action</span>
                  <div className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium ${
                    result.llm_decision.action === "BUY" 
                      ? "bg-emerald/10 text-emerald border border-emerald/20" 
                      : result.llm_decision.action === "SELL"
                      ? "bg-red-500/10 text-red-400 border border-red-500/20"
                      : "bg-gray-500/10 text-gray-400 border border-gray-500/20"
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
                  <span className="text-gray-400">Confidence</span>
                  <span className="font-medium text-white">
                    {(result.llm_decision.confidence * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 rounded-full bg-[#1A1D23] overflow-hidden">
                  <div
                    className="h-full rounded-full bg-emerald transition-all"
                    style={{ width: `${result.llm_decision.confidence * 100}%` }}
                  />
                </div>
              </div>
            </div>

            {result.executed && result.tx_hash && (
              <>
                <div className="h-px bg-[#1F1F24]" />
                
                <div className="p-4 rounded-lg bg-emerald/5 border border-emerald/20">
                  <div className="flex items-center gap-3">
                    <CheckCircle2 className="h-5 w-5 text-emerald" />
                    <div className="flex-1">
                      <span className="text-sm text-gray-400 block mb-1">Trade Executed</span>
                      <a
                        href={`https://explorer.movementnetwork.xyz/txn/${result.tx_hash}?network=mainnet`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-emerald hover:text-emerald-dark font-mono text-sm flex items-center gap-1 transition-colors"
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
