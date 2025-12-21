"use client";

import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { AgentDashboard } from "./components/AgentDashboard";
import { TradeHistory } from "./components/TradeHistory";
import { Header } from "./components/Header";
import { WalletSelectionModal } from "./components/wallet-selection-modal";
import { Button } from "./components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./components/ui/card";
import { Wallet, Sparkles, Loader2 } from "lucide-react";
import { useState, useEffect } from "react";

export default function Home() {
  const { account, connected } = useWallet();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setIsReady(true);
  }, []);

  if (!isReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <div className="text-lg font-medium">Loading...</div>
        </div>
      </div>
    );
  }

  if (!connected) {
    return (
      <>
        <Header />
        <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-gradient-to-br from-background via-background to-muted/20">
          <Card className="w-full max-w-lg shadow-xl border-2">
            <CardHeader className="text-center space-y-4 pb-4">
              <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                <Sparkles className="h-8 w-8 text-primary" />
              </div>
              <div>
                <CardTitle className="text-3xl font-bold">AI Trading Agent</CardTitle>
                <CardDescription className="text-base mt-2">
                  Connect your wallet to start using AI-powered trading on Movement Network
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-3 p-6 pt-0">
              <WalletSelectionModal>
                <Button
                  className="w-full h-11 text-base gap-2"
                  size="lg"
                >
                  <Wallet className="h-5 w-5" />
                  Connect Wallet
                </Button>
              </WalletSelectionModal>
            </CardContent>
          </Card>
        </div>
      </>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/20">
      <Header />
      <main className="container mx-auto py-8 px-4 sm:px-6 lg:px-8">
        <div className="mb-8 space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">Trading Dashboard</h1>
          <p className="text-muted-foreground text-lg">
            Execute AI-powered trades on Movement Network
          </p>
        </div>
        
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <AgentDashboard />
          </div>
          <div className="lg:col-span-1">
            <TradeHistory />
          </div>
        </div>
      </main>
    </div>
  );
}

