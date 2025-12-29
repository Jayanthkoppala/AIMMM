"use client";

import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { usePrivyWallet } from "@/app/hooks/use-privy-wallet";
import { Button } from "./ui/button";
import { WalletSelectionModal } from "./wallet-selection-modal";
import { Wallet, LogOut, Copy, Check, ExternalLink, User, Zap, BookOpen, Bell } from "lucide-react";
import { useState, useEffect } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";

export function Header() {
  const { account, connected, disconnect, wallet } = useWallet();
  const { authenticated, user, login, logout, privyUserId } = usePrivyWallet();
  const [copied, setCopied] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 10);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const handleDisconnect = async () => {
    try {
      if (connected) {
        await disconnect();
      }
    } catch (error) {
      console.error("Failed to disconnect wallet");
    }
  };

  const getAddressString = (): string => {
    if (!account?.address) return "";
    if (typeof account.address === "string") {
      return account.address;
    }
    if (account.address && typeof account.address.toString === "function") {
      return account.address.toString();
    }
    return String(account.address);
  };

  const formatAddress = (address: string) => {
    if (!address) return "";
    return `${address.slice(0, 6)}...${address.slice(-4)}`;
  };

  const addressString = getAddressString();

  const copyAddress = async () => {
    if (addressString) {
      await navigator.clipboard.writeText(addressString);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const viewOnExplorer = () => {
    if (addressString) {
      window.open(
        `https://explorer.movementnetwork.xyz/account/${addressString}?network=mainnet`,
        "_blank",
        "noopener,noreferrer"
      );
    }
  };

  return (
    <header 
      className={`sticky top-0 z-50 w-full transition-all duration-300 ${
        scrolled 
          ? "bg-cyber-bg/95 backdrop-blur-lg border-b border-cyber-indigo/20 shadow-lg" 
          : "bg-transparent"
      }`}
    >
      <div className="container flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyber-indigo to-cyber-purple flex items-center justify-center">
              <Zap className="h-5 w-5 text-white" />
            </div>
            <h1 className="text-xl font-bold text-white">AI Trading Agent</h1>
          </div>
          
          <nav className="hidden md:flex items-center gap-4">
            <a href="#features" className="text-sm text-gray-400 hover:text-white transition-colors">
              Features
            </a>
            <a href="#" className="text-sm text-gray-400 hover:text-white transition-colors flex items-center gap-1">
              <BookOpen className="h-4 w-4" />
              Docs
            </a>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {connected && (
            <Button
              variant="ghost"
              size="icon"
              className="text-gray-400 hover:text-white hover:bg-cyber-card/50"
            >
              <Bell className="h-5 w-5" />
            </Button>
          )}

          {authenticated ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  className="gap-2 h-9 px-3 bg-cyber-card/50 border-cyber-indigo/30 hover:border-cyber-indigo/50 hover:bg-cyber-card"
                >
                  <User className="h-4 w-4 text-cyber-indigo" />
                  <span className="hidden sm:inline text-gray-200">
                    {user?.email?.address?.split("@")[0] || user?.twitter?.username || "User"}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64 bg-cyber-card border-cyber-indigo/20">
                <div className="px-2 py-1.5">
                  <p className="text-xs text-gray-500 mb-1">Privy Account</p>
                  <p className="text-sm font-semibold text-white">
                    {user?.email?.address || user?.twitter?.username || user?.google?.email || "Authenticated"}
                  </p>
                  {privyUserId && (
                    <p className="text-xs text-gray-500 mt-1 font-mono truncate">
                      {privyUserId.slice(0, 8)}...
                    </p>
                  )}
                </div>
                <DropdownMenuSeparator className="bg-cyber-indigo/20" />
                <DropdownMenuItem
                  onClick={logout}
                  className="gap-2 text-cyber-red focus:text-cyber-red focus:bg-cyber-red/10"
                >
                  <LogOut className="h-4 w-4" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="gap-2 bg-cyber-card/50 border-cyber-indigo/30 hover:border-cyber-indigo/50 hover:bg-cyber-card text-gray-200"
              onClick={login}
            >
              <User className="h-4 w-4" />
              <span className="hidden sm:inline">Login</span>
            </Button>
          )}

          {connected ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  className="gap-2 h-9 px-4 cyber-button text-white border-0"
                >
                  <div className="flex items-center gap-2">
                    {wallet?.icon && (
                      <img
                        src={wallet.icon}
                        alt={wallet?.name || "Wallet"}
                        className="w-4 h-4 rounded"
                      />
                    )}
                    <Wallet className="h-4 w-4" />
                    <span className="hidden sm:inline font-mono text-sm">
                      {formatAddress(addressString)}
                    </span>
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64 bg-cyber-card border-cyber-indigo/20">
                <div className="px-2 py-1.5">
                  <p className="text-xs text-gray-500 mb-1">Connected Wallet</p>
                  <div className="flex items-center gap-2">
                    {wallet?.icon && (
                      <img
                        src={wallet.icon}
                        alt={wallet?.name || "Wallet"}
                        className="w-5 h-5 rounded"
                      />
                    )}
                    <p className="text-sm font-semibold text-white">{wallet?.name || "Wallet"}</p>
                  </div>
                </div>
                <DropdownMenuSeparator className="bg-cyber-indigo/20" />
                <div className="px-2 py-1.5">
                  <p className="text-xs text-gray-500 mb-1">Address</p>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-mono flex-1 truncate text-gray-300">
                      {addressString}
                    </p>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 hover:bg-cyber-indigo/20"
                      onClick={copyAddress}
                    >
                      {copied ? (
                        <Check className="h-3 w-3 text-cyber-green" />
                      ) : (
                        <Copy className="h-3 w-3 text-gray-400" />
                      )}
                    </Button>
                  </div>
                </div>
                <DropdownMenuSeparator className="bg-cyber-indigo/20" />
                <DropdownMenuItem onClick={viewOnExplorer} className="gap-2 text-gray-300 focus:bg-cyber-indigo/10">
                  <ExternalLink className="h-4 w-4" />
                  View on Explorer
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-cyber-indigo/20" />
                <DropdownMenuItem
                  onClick={handleDisconnect}
                  className="gap-2 text-cyber-red focus:text-cyber-red focus:bg-cyber-red/10"
                >
                  <LogOut className="h-4 w-4" />
                  Disconnect Wallet
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <WalletSelectionModal>
              <Button className="gap-2 cyber-button text-white border-0 px-4">
                <Wallet className="h-4 w-4" />
                <span className="hidden sm:inline">Connect Wallet</span>
                <span className="sm:hidden">Connect</span>
              </Button>
            </WalletSelectionModal>
          )}
        </div>
      </div>
    </header>
  );
}
