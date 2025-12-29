"use client";

import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { Header } from "./components/Header";
import { LandingPage } from "./components/LandingPage";
import { Dashboard } from "./components/Dashboard";
import { Loader2 } from "lucide-react";
import { useState, useEffect } from "react";

export default function Home() {
  const { connected } = useWallet();
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    setIsReady(true);
  }, []);

  if (!isReady) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-cyber-bg">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-cyber-indigo" />
          <div className="text-lg font-medium text-white">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header />
      {connected ? <Dashboard /> : <LandingPage />}
    </div>
  );
}
