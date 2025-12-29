"use client";

import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { usePrivyWallet } from "@/app/hooks/use-privy-wallet";
import { Button } from "./ui/button";
import { WalletSelectionModal } from "./wallet-selection-modal";
import { Wallet, LogOut, Copy, Check, ExternalLink, User, Zap } from "lucide-react";
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
      className={`sticky top-0 z-50 w-full transition-all duration-200 ${
        scrolled 
          ? "bg-[#060608]/95 backdrop-blur-sm border-b border-[#1F1F24]" 
          : "bg-transparent"
      }`}
    >
      <div className="container flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald flex items-center justify-center">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <h1 className="text-lg font-semibold text-white tracking-tight">AI Trading Agent</h1>
          </div>
          
          <nav className="hidden md:flex items-center gap-6">
            <a href="#features" className="text-sm text-gray-400 hover:text-white transition-colors">
              Features
            </a>
            <a href="#" className="text-sm text-gray-400 hover:text-white transition-colors">
              Docs
            </a>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {authenticated ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  className="gap-2 h-9 px-3 bg-transparent border-[#2A2D33] hover:border-emerald hover:bg-transparent"
                >
                  <User className="h-4 w-4 text-emerald" />
                  <span className="hidden sm:inline text-white text-sm">
                    {user?.email?.address?.split("@")[0] || user?.twitter?.username || "User"}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64 bg-[#111317] border-[#2A2D33]">
                <div className="px-3 py-2">
                  <p className="text-xs text-gray-500 mb-1">Account</p>
                  <p className="text-sm font-medium text-white">
                    {user?.email?.address || user?.twitter?.username || user?.google?.email || "Authenticated"}
                  </p>
                </div>
                <DropdownMenuSeparator className="bg-[#2A2D33]" />
                <DropdownMenuItem
                  onClick={logout}
                  className="gap-2 text-red-400 focus:text-red-400 focus:bg-red-500/10"
                >
                  <LogOut className="h-4 w-4" />
                  Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button
              variant="outline"
              size="sm"
              className="gap-2 bg-transparent border-[#2A2D33] hover:border-emerald text-white"
              onClick={login}
            >
              <User className="h-4 w-4" />
              <span className="hidden sm:inline">Sign In</span>
            </Button>
          )}

          {connected ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button className="gap-2 h-9 px-4 bg-emerald hover:bg-emerald-dark text-white border-0">
                  <div className="flex items-center gap-2">
                    {wallet?.icon && (
                      <img
                        src={wallet.icon}
                        alt={wallet?.name || "Wallet"}
                        className="w-4 h-4 rounded"
                      />
                    )}
                    <span className="hidden sm:inline font-mono text-sm">
                      {formatAddress(addressString)}
                    </span>
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64 bg-[#111317] border-[#2A2D33]">
                <div className="px-3 py-2">
                  <p className="text-xs text-gray-500 mb-1">Connected Wallet</p>
                  <div className="flex items-center gap-2">
                    {wallet?.icon && (
                      <img
                        src={wallet.icon}
                        alt={wallet?.name || "Wallet"}
                        className="w-5 h-5 rounded"
                      />
                    )}
                    <p className="text-sm font-medium text-white">{wallet?.name || "Wallet"}</p>
                  </div>
                </div>
                <DropdownMenuSeparator className="bg-[#2A2D33]" />
                <div className="px-3 py-2">
                  <p className="text-xs text-gray-500 mb-1">Address</p>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-mono flex-1 truncate text-gray-300">
                      {addressString}
                    </p>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 hover:bg-emerald/10"
                      onClick={copyAddress}
                    >
                      {copied ? (
                        <Check className="h-3 w-3 text-emerald" />
                      ) : (
                        <Copy className="h-3 w-3 text-gray-400" />
                      )}
                    </Button>
                  </div>
                </div>
                <DropdownMenuSeparator className="bg-[#2A2D33]" />
                <DropdownMenuItem onClick={viewOnExplorer} className="gap-2 text-gray-300 focus:bg-emerald/10">
                  <ExternalLink className="h-4 w-4" />
                  View on Explorer
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-[#2A2D33]" />
                <DropdownMenuItem
                  onClick={handleDisconnect}
                  className="gap-2 text-red-400 focus:text-red-400 focus:bg-red-500/10"
                >
                  <LogOut className="h-4 w-4" />
                  Disconnect
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <WalletSelectionModal>
              <Button className="gap-2 bg-emerald hover:bg-emerald-dark text-white border-0 px-4">
                <Wallet className="h-4 w-4" />
                <span className="hidden sm:inline">Connect Wallet</span>
              </Button>
            </WalletSelectionModal>
          )}
        </div>
      </div>
    </header>
  );
}
