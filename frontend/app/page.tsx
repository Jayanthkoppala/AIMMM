"use client";

import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { usePrivyWallet } from "./hooks/use-privy-wallet";
import { Header } from "./components/Header";
import { LandingPage } from "./components/LandingPage";
import { Dashboard } from "./components/Dashboard";
import { Loader2 } from "lucide-react";
import { useState, useEffect } from "react";

export default function Home() {
  const { connected } = useWallet();
  const { authenticated } = usePrivyWallet();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const isLoggedIn = connected || authenticated;

  if (!mounted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#060608]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-emerald" />
          <div className="text-lg font-medium text-white">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Header />
      {isLoggedIn ? <Dashboard /> : <LandingPage />}
    </div>
  );
}
