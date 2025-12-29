"use client";

import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { usePrivyWallet } from "@/app/hooks/use-privy-wallet";
import { Button } from "./ui/button";
import { LogOut, Copy, Check, ExternalLink, User, Terminal } from "lucide-react";
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
  const { authenticated, user, login, logout } = usePrivyWallet();
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
          ? "bg-[#0a0a0a]/95 backdrop-blur-sm border-b border-[#1a1a1a]" 
          : "bg-transparent"
      }`}
    >
      <div className="container flex h-14 items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 border border-[#00ff00] flex items-center justify-center glow-border">
              <Terminal className="h-4 w-4 text-[#00ff00]" />
            </div>
            <h1 className="text-sm font-bold text-[#00ff00] tracking-wider font-mono">
              AI_AGENT
            </h1>
          </div>
          
          <nav className="hidden md:flex items-center gap-6 font-mono">
            <a href="#features" className="text-xs text-[#006600] hover:text-[#00ff00] transition-colors uppercase tracking-wider">
              [Modules]
            </a>
            <a href="#" className="text-xs text-[#006600] hover:text-[#00ff00] transition-colors uppercase tracking-wider">
              [Docs]
            </a>
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {authenticated ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="outline"
                  className="gap-2 h-8 px-3 bg-transparent border-[#00ff00] hover:bg-[#00ff00] hover:text-[#0a0a0a] text-[#00ff00] font-mono text-xs"
                >
                  <User className="h-3 w-3" />
                  <span className="hidden sm:inline uppercase">
                    {user?.email?.address?.split("@")[0] || user?.twitter?.username || "user"}
                  </span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-64 bg-[#0f0f0f] border-[#00ff00] font-mono">
                <div className="px-3 py-2">
                  <p className="text-[10px] text-[#006600] mb-1 uppercase">// Session</p>
                  <p className="text-xs text-[#00ff00]">
                    {user?.email?.address || user?.twitter?.username || user?.google?.email || "authenticated"}
                  </p>
                </div>
                <DropdownMenuSeparator className="bg-[#1a1a1a]" />
                <DropdownMenuItem
                  onClick={logout}
                  className="gap-2 text-[#ff3333] focus:text-[#ff3333] focus:bg-[#ff3333]/10 font-mono text-xs"
                >
                  <LogOut className="h-3 w-3" />
                  ./logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button
              size="sm"
              className="gap-2 btn-terminal text-xs h-8"
              onClick={login}
            >
              <User className="h-3 w-3" />
              <span className="hidden sm:inline">./login</span>
            </Button>
          )}

          {connected && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button className="gap-2 h-8 px-4 btn-terminal-filled text-xs">
                  <div className="flex items-center gap-2">
                    {wallet?.icon && (
                      <img
                        src={wallet.icon}
                        alt={wallet?.name || "Wallet"}
                        className="w-3 h-3"
                      />
                    )}
                    <span className="hidden sm:inline font-mono">
                      {formatAddress(addressString)}
                    </span>
                  </div>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-72 bg-[#0f0f0f] border-[#00ff00] font-mono">
                <div className="px-3 py-2">
                  <p className="text-[10px] text-[#006600] mb-1 uppercase">// Wallet Connected</p>
                  <div className="flex items-center gap-2">
                    {wallet?.icon && (
                      <img
                        src={wallet.icon}
                        alt={wallet?.name || "Wallet"}
                        className="w-4 h-4"
                      />
                    )}
                    <p className="text-xs text-[#00ff00]">{wallet?.name || "wallet"}</p>
                  </div>
                </div>
                <DropdownMenuSeparator className="bg-[#1a1a1a]" />
                <div className="px-3 py-2">
                  <p className="text-[10px] text-[#006600] mb-1 uppercase">// Address</p>
                  <div className="flex items-center gap-2">
                    <p className="text-xs font-mono flex-1 truncate text-[#00aa00]">
                      {addressString}
                    </p>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 hover:bg-[#00ff00]/10"
                      onClick={copyAddress}
                    >
                      {copied ? (
                        <Check className="h-3 w-3 text-[#00ff00]" />
                      ) : (
                        <Copy className="h-3 w-3 text-[#006600]" />
                      )}
                    </Button>
                  </div>
                </div>
                <DropdownMenuSeparator className="bg-[#1a1a1a]" />
                <DropdownMenuItem onClick={viewOnExplorer} className="gap-2 text-[#00aa00] focus:bg-[#00ff00]/10 text-xs">
                  <ExternalLink className="h-3 w-3" />
                  ./view_explorer
                </DropdownMenuItem>
                <DropdownMenuSeparator className="bg-[#1a1a1a]" />
                <DropdownMenuItem
                  onClick={handleDisconnect}
                  className="gap-2 text-[#ff3333] focus:text-[#ff3333] focus:bg-[#ff3333]/10 text-xs"
                >
                  <LogOut className="h-3 w-3" />
                  ./disconnect
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>
    </header>
  );
}
