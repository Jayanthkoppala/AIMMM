"use client";

import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { Button } from "./ui/button";
import { WalletSelectionModal } from "./wallet-selection-modal";
import { Wallet, LogOut, Activity, Copy, Check, ExternalLink } from "lucide-react";
import { Badge } from "./ui/badge";
import { useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";

export function Header() {
  const { account, connected, disconnect, wallet } = useWallet();
  const [copied, setCopied] = useState(false);

  const handleDisconnect = async () => {
    try {
      if (connected) {
        await disconnect();
      }
    } catch (error) {
      console.error("Failed to disconnect wallet");
    }
  };

  // Get address as string, handling different types
  const getAddressString = (): string => {
    if (!account?.address) return "";
    // Handle both string and object types
    if (typeof account.address === "string") {
      return account.address;
    }
    // If it's an object with toString method
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
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <Activity className="h-6 w-6 text-primary" />
            <h1 className="text-xl font-bold">AI Trading Agent</h1>
          </div>
          <Badge variant="outline" className="ml-2 hidden sm:inline-flex">
            Movement Network
          </Badge>
        </div>

        <div className="flex items-center gap-3">
          {connected ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  className="gap-2 h-9 px-3"
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
                    <span className="sm:hidden font-mono text-xs">
                      {addressString ? `${addressString.slice(0, 4)}...${addressString.slice(-2)}` : ""}
                    </span>
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64">
                <div className="px-2 py-1.5">
                  <p className="text-xs text-muted-foreground mb-1">Connected Wallet</p>
                  <div className="flex items-center gap-2">
                    {wallet?.icon && (
                      <img
                        src={wallet.icon}
                        alt={wallet?.name || "Wallet"}
                        className="w-5 h-5 rounded"
                      />
                    )}
                    <p className="text-sm font-semibold">{wallet?.name || "Wallet"}</p>
                  </div>
                </div>
                <DropdownMenuSeparator />
                <div className="px-2 py-1.5">
                  <p className="text-xs text-muted-foreground mb-1">Address</p>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-mono flex-1 truncate">
                      {addressString}
                    </p>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={copyAddress}
                    >
                      {copied ? (
                        <Check className="h-3 w-3 text-green-500" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={viewOnExplorer} className="gap-2">
                  <ExternalLink className="h-4 w-4" />
                  View on Explorer
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={handleDisconnect}
                  className="gap-2 text-destructive focus:text-destructive"
                >
                  <LogOut className="h-4 w-4" />
                  Disconnect Wallet
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <WalletSelectionModal>
              <Button
                variant="default"
                size="sm"
                className="gap-2"
              >
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

