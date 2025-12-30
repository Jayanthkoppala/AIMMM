"use client";

import { useState, useEffect } from "react";
import { usePrivyWallet } from "@/app/hooks/use-privy-wallet";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Play, Pause, Activity, Wallet } from "lucide-react";
import { toast } from "sonner";

export function AutonomousTrading() {
  const { authenticated, user, privyUserId, login, getAccessToken } = usePrivyWallet();
  const [isActive, setIsActive] = useState(false);
  const [walletAddress, setWalletAddress] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Fetch autonomous wallet status
  useEffect(() => {
    if (authenticated && privyUserId) {
      fetchWalletStatus();
    }
  }, [authenticated, privyUserId]);

  const fetchWalletStatus = async () => {
    try {
      const token = await getAccessToken();
      const response = await fetch("/api/autonomous/status", {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setWalletAddress(data.wallet_address);
        setIsActive(data.enabled);
      }
    } catch (error) {
      console.error("Failed to fetch wallet status:", error);
    }
  };

  const toggleAutonomous = async () => {
    setLoading(true);
    try {
      const token = await getAccessToken();
      const response = await fetch("/api/autonomous/toggle", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({ enabled: !isActive })
      });

      if (response.ok) {
        setIsActive(!isActive);
        toast.success(
          isActive 
            ? "Autonomous trading disabled" 
            : "Autonomous trading enabled"
        );
        // Refresh wallet status
        await fetchWalletStatus();
      } else {
        const errorData = await response.json();
        toast.error(errorData.detail || "Failed to toggle autonomous trading");
      }
    } catch (error) {
      toast.error("Failed to toggle autonomous trading");
    } finally {
      setLoading(false);
    }
  };

  if (!authenticated) {
    return (
      <Card className="border-2 border-purple-500/50">
        <CardContent className="pt-6">
          <Button onClick={login} className="w-full">
            Login with Privy to Enable Autonomous Trading
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-2 border-purple-500/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5 text-purple-600" />
            <CardTitle>Autonomous Trading</CardTitle>
          </div>
          <Badge variant={isActive ? "default" : "secondary"}>
            {isActive ? "Active" : "Inactive"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">
          Your AI agent will monitor markets and execute trades automatically every 5 minutes.
        </p>
        
        {walletAddress && (
          <div className="p-3 rounded-lg bg-muted flex items-center gap-2">
            <Wallet className="h-4 w-4 text-muted-foreground" />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-muted-foreground">Autonomous Wallet</p>
              <p className="font-mono text-sm truncate">{walletAddress}</p>
            </div>
          </div>
        )}
        
        <Button
          onClick={toggleAutonomous}
          disabled={loading}
          className="w-full"
          variant={isActive ? "destructive" : "default"}
        >
          {loading ? (
            "Processing..."
          ) : isActive ? (
            <>
              <Pause className="h-4 w-4 mr-2" />
              Pause Autonomous Trading
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Start Autonomous Trading
            </>
          )}
        </Button>
      </CardContent>
    </Card>
  );
}


