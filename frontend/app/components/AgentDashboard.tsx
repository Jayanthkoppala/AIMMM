"use client";

import { useState } from "react";
import { useAgent } from "@/app/hooks/use-agent";
import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { usePrivyWallet } from "@/app/hooks/use-privy-wallet";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { Select } from "./ui/select";
import { 
  Play, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Brain, 
  CheckCircle2, 
  ExternalLink,
  Loader2,
  BarChart3,
  Zap,
  Sparkles
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
        privy_access_token: accessToken,
      });
    } catch (error) {
      console.error("Agent execution failed:", error);
    }
  };

  return (
    <div className="space-y-6">
      <Card className="shadow-lg border-2">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            <CardTitle className="text-2xl">AI Trading Agent</CardTitle>
          </div>
          <CardDescription className="text-base">
            Configure your trading agent and execute trades on Mosaic DEX
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Mode Selection */}
          <div className="space-y-3">
            <Label className="text-base font-semibold">Execution Mode</Label>
            <div className="flex gap-3">
              <Button
                variant={mode === "analysis" ? "default" : "outline"}
                onClick={() => setMode("analysis")}
                className="flex-1 h-11 gap-2"
                size="lg"
              >
                <BarChart3 className="h-4 w-4" />
                Analysis Only
              </Button>
              <Button
                variant={mode === "trade" ? "default" : "outline"}
                onClick={() => setMode("trade")}
                className="flex-1 h-11 gap-2"
                size="lg"
              >
                <Zap className="h-4 w-4" />
                Execute Trade
              </Button>
              <Button
                variant={mode === "autonomous" ? "default" : "outline"}
                onClick={() => setMode("autonomous")}
                className="flex-1 h-11 gap-2 bg-purple-600 hover:bg-purple-700"
                size="lg"
              >
                <Sparkles className="h-4 w-4" />
                Autonomous
              </Button>
            </div>
            {mode === "autonomous" && (
              <div className="p-4 rounded-lg bg-purple-50 dark:bg-purple-950/20 border border-purple-200 dark:border-purple-800">
                <div className="flex items-start gap-2">
                  <Sparkles className="h-5 w-5 text-purple-600 mt-0.5" />
                  <div>
                    <p className="font-semibold text-purple-900 dark:text-purple-100">
                      Autonomous Trading Enabled
                    </p>
                    <p className="text-sm text-purple-700 dark:text-purple-300 mt-1">
                      Your AI agent will execute trades automatically based on market conditions.
                      No manual approval needed - powered by Privy embedded wallets.
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>

          <Separator />

          {/* Token Pair */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="tokenA" className="text-base font-semibold">Token A Address</Label>
              <Input
                id="tokenA"
                type="text"
                value={tokenA}
                onChange={(e) => setTokenA(e.target.value)}
                placeholder="0x..."
                className="font-mono"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tokenB" className="text-base font-semibold">Token B Address</Label>
              <Input
                id="tokenB"
                type="text"
                value={tokenB}
                onChange={(e) => setTokenB(e.target.value)}
                placeholder="0x..."
                className="font-mono"
              />
            </div>
          </div>

          {/* Pool Address */}
          <div className="space-y-2">
            <Label htmlFor="poolAddress" className="text-base font-semibold">Pool Address</Label>
            <Input
              id="poolAddress"
              type="text"
              value={poolAddress}
              onChange={(e) => setPoolAddress(e.target.value)}
              placeholder="0xbcbf55e1004687d412f05856ef7c17dcaacc1be632ba2d67b71073d25b425c3b"
              className="font-mono"
            />
            <p className="text-xs text-muted-foreground">
              Enter the pool address for this token pair (data is collected automatically by the scheduler)
            </p>
          </div>

          <Separator />

          {/* Run Button */}
          <Button
            onClick={handleRunAgent}
            disabled={isLoading || (mode !== "autonomous" && !connected) || (mode === "autonomous" && !authenticated)}
            className="w-full h-12 text-base gap-2"
            size="lg"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Play className="h-5 w-5" />
                Run Agent
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <Card className="shadow-lg border-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              <CardTitle className="text-2xl">Execution Results</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Oracle Prices */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <DollarSign className="h-5 w-5 text-muted-foreground" />
                <h3 className="font-semibold text-lg">Oracle Prices</h3>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-muted/50 border">
                  <div className="text-sm text-muted-foreground mb-1">Token A</div>
                  <div className="text-2xl font-bold font-mono">
                    ${result.oracle_price.token_a.toFixed(4)}
                  </div>
                </div>
                <div className="p-4 rounded-lg bg-muted/50 border">
                  <div className="text-sm text-muted-foreground mb-1">Token B</div>
                  <div className="text-2xl font-bold font-mono">
                    ${result.oracle_price.token_b.toFixed(4)}
                  </div>
                </div>
              </div>
            </div>

            <Separator />

            {/* LLM Decision */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-primary" />
                <h3 className="font-semibold text-lg">AI Decision</h3>
              </div>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50 border">
                  <span className="text-muted-foreground font-medium">Action</span>
                  <Badge 
                    variant={
                      result.llm_decision.action === "BUY" ? "success" :
                      result.llm_decision.action === "SELL" ? "destructive" :
                      "secondary"
                    }
                    className="text-base px-3 py-1"
                  >
                    {result.llm_decision.action === "BUY" && <TrendingUp className="h-4 w-4 mr-1" />}
                    {result.llm_decision.action === "SELL" && <TrendingDown className="h-4 w-4 mr-1" />}
                    {result.llm_decision.action}
                  </Badge>
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground font-medium">Confidence</span>
                    <span className="font-semibold">
                      {(result.llm_decision.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-muted rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-primary h-full rounded-full transition-all duration-500"
                      style={{ width: `${result.llm_decision.confidence * 100}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Execution Status */}
            {result.executed && result.tx_hash && (
              <>
                <Separator />
                <div className="space-y-3">
                  <h3 className="font-semibold text-lg">Trade Executed</h3>
                  <div className="flex items-center gap-2 p-4 rounded-lg bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800">
                    <CheckCircle2 className="h-5 w-5 text-green-600" />
                    <div className="flex-1">
                      <div className="text-sm text-muted-foreground mb-1">Transaction Hash</div>
                      <a
                        href={`https://explorer.movementnetwork.xyz/txn/${result.tx_hash}?network=testnet`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline font-mono text-sm flex items-center gap-1"
                      >
                        {result.tx_hash.slice(0, 16)}...{result.tx_hash.slice(-8)}
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

