"use client";

import { useState, useEffect } from "react";
import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { getExplorerUrl } from "@/app/lib/aptos";
import { 
  History, 
  TrendingUp, 
  TrendingDown, 
  Clock, 
  DollarSign, 
  ExternalLink,
  Loader2,
  Inbox
} from "lucide-react";

interface TradeHistoryItem {
  id: string;
  mode: string;
  token_a_address: string;
  token_b_address: string;
  llm_action: string;
  llm_confidence: number;
  executed: boolean;
  tx_hash: string | null;
  execution_cost: number;
  created_at: string;
}

export function TradeHistory() {
  const { account } = useWallet();
  const [trades, setTrades] = useState<TradeHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In production, fetch from Supabase via backend API
    // For now, show empty state
    setLoading(false);
  }, [account]);

  if (loading) {
    return (
      <Card className="shadow-lg border-2">
        <CardContent className="p-8">
          <div className="flex flex-col items-center justify-center gap-3 text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin" />
            <div>Loading trade history...</div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (trades.length === 0) {
    return (
      <Card className="shadow-lg border-2">
        <CardHeader>
          <div className="flex items-center gap-2">
            <History className="h-5 w-5 text-primary" />
            <CardTitle className="text-xl">Trade History</CardTitle>
          </div>
          <CardDescription>
            View your past trading activity and executions
          </CardDescription>
        </CardHeader>
        <CardContent className="p-8">
          <div className="flex flex-col items-center justify-center gap-4 text-center">
            <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center">
              <Inbox className="h-8 w-8 text-muted-foreground" />
            </div>
            <div className="space-y-1">
              <div className="font-medium">No trades yet</div>
              <div className="text-sm text-muted-foreground">
                Execute your first agent run to see history here
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-lg border-2">
      <CardHeader>
        <div className="flex items-center gap-2">
          <History className="h-5 w-5 text-primary" />
          <CardTitle className="text-xl">Trade History</CardTitle>
        </div>
        <CardDescription>
          View your past trading activity and executions
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {trades.map((trade) => (
            <div 
              key={trade.id} 
              className="border rounded-lg p-4 space-y-3 hover:bg-muted/50 transition-colors"
            >
              <div className="flex justify-between items-start">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge 
                      variant={
                        trade.llm_action === "BUY" ? "success" :
                        trade.llm_action === "SELL" ? "destructive" :
                        "secondary"
                      }
                      className="text-xs"
                    >
                      {trade.llm_action === "BUY" && <TrendingUp className="h-3 w-3 mr-1" />}
                      {trade.llm_action === "SELL" && <TrendingDown className="h-3 w-3 mr-1" />}
                      {trade.llm_action}
                    </Badge>
                    <Badge variant="outline" className="text-xs">
                      {trade.mode}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {new Date(trade.created_at).toLocaleString()}
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-3 pt-2 border-t">
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Confidence</div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-muted rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-primary h-full rounded-full"
                        style={{ width: `${trade.llm_confidence * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-semibold">
                      {(trade.llm_confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-xs text-muted-foreground">Cost</div>
                  <div className="flex items-center gap-1">
                    <DollarSign className="h-3 w-3 text-muted-foreground" />
                    <span className="text-sm font-semibold font-mono">
                      {trade.execution_cost.toFixed(4)}
                    </span>
                    <span className="text-xs text-muted-foreground">USDC</span>
                  </div>
                </div>
              </div>

              {trade.executed && trade.tx_hash && (
                <div className="pt-2">
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full gap-2"
                    asChild
                  >
                    <a
                      href={getExplorerUrl(trade.tx_hash)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm"
                    >
                      View Transaction
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

