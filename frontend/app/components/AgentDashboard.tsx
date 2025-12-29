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
  ArrowRight,
  Terminal
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
    <div className="space-y-6 font-mono">
      <div className="terminal-window">
        <div className="terminal-header">
          <div className="terminal-dot red"></div>
          <div className="terminal-dot yellow"></div>
          <div className="terminal-dot green"></div>
          <span className="terminal-title">agent_control.sh</span>
        </div>
        <div className="terminal-body">
          <div className="flex items-center gap-3 mb-6">
            <Brain className="h-5 w-5 text-[#00ff00]" />
            <div>
              <h2 className="text-sm text-[#00ff00] uppercase font-bold">{"// AI Agent Control"}</h2>
              <p className="text-xs text-[#006600]">Configure and execute trading strategies</p>
            </div>
          </div>

          <div className="space-y-6">
            <div className="space-y-3">
              <Label className="text-xs text-[#006600] uppercase">{">"} Select Mode</Label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => setMode("analysis")}
                  className={`flex flex-col items-center gap-2 p-4 transition-all border ${
                    mode === "analysis"
                      ? "border-[#00ff00] bg-[#00ff00]/10 text-[#00ff00] glow-border"
                      : "border-[#1a1a1a] text-[#006600] hover:border-[#00ff00] hover:text-[#00aa00]"
                  }`}
                >
                  <BarChart3 className="h-5 w-5" />
                  <span className="text-xs font-bold uppercase">Analyze</span>
                </button>
                <button
                  onClick={() => setMode("trade")}
                  className={`flex flex-col items-center gap-2 p-4 transition-all border ${
                    mode === "trade"
                      ? "border-[#00ff00] bg-[#00ff00]/10 text-[#00ff00] glow-border"
                      : "border-[#1a1a1a] text-[#006600] hover:border-[#00ff00] hover:text-[#00aa00]"
                  }`}
                >
                  <Zap className="h-5 w-5" />
                  <span className="text-xs font-bold uppercase">Trade</span>
                </button>
                <button
                  onClick={() => setMode("autonomous")}
                  className={`flex flex-col items-center gap-2 p-4 transition-all border ${
                    mode === "autonomous"
                      ? "border-[#00ff00] bg-[#00ff00]/10 text-[#00ff00] glow-border"
                      : "border-[#1a1a1a] text-[#006600] hover:border-[#00ff00] hover:text-[#00aa00]"
                  }`}
                >
                  <Sparkles className="h-5 w-5" />
                  <span className="text-xs font-bold uppercase">Auto</span>
                </button>
              </div>
              
              {mode === "autonomous" && (
                <div className="p-4 border border-[#00ff00] bg-[#00ff00]/5">
                  <div className="flex items-start gap-3">
                    <Sparkles className="h-4 w-4 text-[#00ff00] mt-0.5" />
                    <div>
                      <p className="text-xs text-[#00ff00] uppercase font-bold">[Autonomous Mode]</p>
                      <p className="text-xs text-[#006600] mt-1">
                        AI executes trades automatically via Privy embedded wallets.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="h-px bg-gradient-to-r from-transparent via-[#00ff00]/30 to-transparent" />

            <div className="space-y-3">
              <Label className="text-xs text-[#006600] uppercase">{">"} Token Pair</Label>
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <Input
                    value={tokenA}
                    onChange={(e) => setTokenA(e.target.value)}
                    placeholder="token_a_address"
                    className="text-xs bg-[#0a0a0a] border-[#1a1a1a] focus:border-[#00ff00] text-[#00ff00] placeholder:text-[#004400]"
                  />
                </div>
                <ArrowRight className="h-4 w-4 text-[#006600] flex-shrink-0" />
                <div className="flex-1">
                  <Input
                    value={tokenB}
                    onChange={(e) => setTokenB(e.target.value)}
                    placeholder="token_b_address"
                    className="text-xs bg-[#0a0a0a] border-[#1a1a1a] focus:border-[#00ff00] text-[#00ff00] placeholder:text-[#004400]"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label className="text-xs text-[#006600] uppercase">{">"} Pool Address</Label>
              <Input
                value={poolAddress}
                onChange={(e) => setPoolAddress(e.target.value)}
                placeholder="pool_address"
                className="text-xs bg-[#0a0a0a] border-[#1a1a1a] focus:border-[#00ff00] text-[#00ff00] placeholder:text-[#004400]"
              />
            </div>

            <div className="h-px bg-gradient-to-r from-transparent via-[#00ff00]/30 to-transparent" />

            <Button
              onClick={handleRunAgent}
              disabled={isLoading || (mode !== "autonomous" && !connected) || (mode === "autonomous" && !authenticated)}
              className={`w-full h-12 text-sm font-bold uppercase tracking-wider ${
                isLoading 
                  ? "bg-[#1a1a1a] text-[#006600] border border-[#1a1a1a]" 
                  : "btn-terminal-filled"
              }`}
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  ./execute --run
                </>
              )}
            </Button>
          </div>
        </div>
      </div>

      {result && (
        <div className="terminal-window animate-fade-in">
          <div className="terminal-header">
            <div className="terminal-dot red"></div>
            <div className="terminal-dot yellow"></div>
            <div className="terminal-dot green"></div>
            <span className="terminal-title">output.log</span>
          </div>
          <div className="terminal-body">
            <div className="flex items-center gap-3 mb-6">
              <CheckCircle2 className="h-5 w-5 text-[#00ff00]" />
              <div>
                <h2 className="text-sm text-[#00ff00] uppercase font-bold">{"// Analysis Complete"}</h2>
                <p className="text-xs text-[#006600]">[STATUS: SUCCESS]</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="h-4 w-4 text-[#006600]" />
                  <span className="text-xs text-[#006600] uppercase">Oracle Prices</span>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                    <span className="text-[10px] text-[#006600] block mb-1">token_a</span>
                    <span className="text-lg font-bold text-[#00ff00] glow-text-subtle">
                      ${result.oracle_price.token_a.toFixed(4)}
                    </span>
                  </div>
                  <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a]">
                    <span className="text-[10px] text-[#006600] block mb-1">token_b</span>
                    <span className="text-lg font-bold text-[#00ff00] glow-text-subtle">
                      ${result.oracle_price.token_b.toFixed(4)}
                    </span>
                  </div>
                </div>
              </div>

              <div className="h-px bg-gradient-to-r from-transparent via-[#00ff00]/30 to-transparent" />

              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Brain className="h-4 w-4 text-[#00ff00]" />
                  <span className="text-xs text-[#00ff00] uppercase">AI Decision</span>
                </div>
                
                <div className="p-3 bg-[#0a0a0a] border border-[#1a1a1a] mb-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[#006600] text-xs">recommended_action:</span>
                    <div className={`flex items-center gap-2 px-3 py-1 text-xs font-bold border ${
                      result.llm_decision.action === "BUY" 
                        ? "border-[#00ff00] text-[#00ff00] bg-[#00ff00]/10" 
                        : result.llm_decision.action === "SELL"
                        ? "border-[#ff3333] text-[#ff3333] bg-[#ff3333]/10"
                        : "border-[#006600] text-[#006600] bg-[#006600]/10"
                    }`}>
                      {result.llm_decision.action === "BUY" && <TrendingUp className="h-3 w-3" />}
                      {result.llm_decision.action === "SELL" && <TrendingDown className="h-3 w-3" />}
                      {result.llm_decision.action === "HOLD" && <Minus className="h-3 w-3" />}
                      {result.llm_decision.action}
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-[#006600]">confidence_level:</span>
                    <span className="font-bold text-[#00ff00]">
                      {(result.llm_decision.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="h-2 bg-[#0a0a0a] border border-[#1a1a1a] overflow-hidden">
                    <div
                      className="h-full bg-[#00ff00] transition-all"
                      style={{ width: `${result.llm_decision.confidence * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              {result.executed && result.tx_hash && (
                <>
                  <div className="h-px bg-gradient-to-r from-transparent via-[#00ff00]/30 to-transparent" />
                  
                  <div className="p-3 border border-[#00ff00] bg-[#00ff00]/5">
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="h-4 w-4 text-[#00ff00]" />
                      <div className="flex-1">
                        <span className="text-[10px] text-[#006600] block mb-1">[TRADE_EXECUTED]</span>
                        <a
                          href={`https://explorer.movementnetwork.xyz/txn/${result.tx_hash}?network=mainnet`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[#00ff00] hover:underline text-xs flex items-center gap-1"
                        >
                          tx: {result.tx_hash.slice(0, 16)}...{result.tx_hash.slice(-8)}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
