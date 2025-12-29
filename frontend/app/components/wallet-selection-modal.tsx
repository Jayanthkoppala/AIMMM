"use client";

import { useState } from "react";
import { useWallet } from "@aptos-labs/wallet-adapter-react";
import { Button } from "@/app/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/app/components/ui/dialog";
import { ExternalLink, Loader2 } from "lucide-react";

interface WalletSelectionModalProps {
  children: React.ReactNode;
}

const WALLET_INSTALL_LINKS = [
  {
    name: "Nightly",
    url: "https://nightly.app/download",
    icon: "https://nightly.app/favicon.ico",
    description: "Recommended for Movement Network",
  },
  {
    name: "Petra",
    url: "https://petra.app/",
    icon: "https://petra.app/favicon.ico",
    description: "Popular Aptos wallet",
  },
];

export function WalletSelectionModal({ children }: WalletSelectionModalProps) {
  const [open, setOpen] = useState(false);
  const [connecting, setConnecting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { wallets, connect, connected } = useWallet();

  const availableWallets = wallets.filter((wallet) => {
    const name = wallet.name.toLowerCase();
    return !name.includes("google") && !name.includes("apple");
  }).filter((wallet, index, self) => {
    return index === self.findIndex((w) => w.name === wallet.name);
  }).sort((a, b) => {
    if (a.name.toLowerCase().includes("nightly")) return -1;
    if (b.name.toLowerCase().includes("nightly")) return 1;
    return 0;
  });

  const handleWalletSelect = async (walletName: string) => {
    setConnecting(walletName);
    setError(null);
    
    try {
      await connect(walletName);
      setOpen(false);
    } catch (err: any) {
      const message = err?.message || String(err);
      if (message.includes("rejected")) {
        setError("Connection was cancelled. Please try again.");
      } else if (message.includes("not installed") || message.includes("not found")) {
        setError(`${walletName} is not installed. Please install it first.`);
      } else {
        setError("Failed to connect. Make sure your wallet is unlocked and try again.");
      }
    } finally {
      setConnecting(null);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(isOpen) => {
      setOpen(isOpen);
      if (!isOpen) {
        setError(null);
        setConnecting(null);
      }
    }}>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md bg-[#111317] border-[#2A2D33]">
        <DialogHeader>
          <DialogTitle className="text-white">Connect Wallet</DialogTitle>
          <DialogDescription className="text-gray-400">
            Connect to Movement Network
          </DialogDescription>
        </DialogHeader>
        
        {error && (
          <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            {error}
          </div>
        )}

        <div className="space-y-2">
          {availableWallets.length > 0 ? (
            availableWallets.map((wallet) => (
              <Button
                key={wallet.name}
                variant="outline"
                className="w-full justify-start h-12 bg-[#1A1D23] border-[#2A2D33] hover:border-emerald hover:bg-[#1A1D23] text-white"
                onClick={() => handleWalletSelect(wallet.name)}
                disabled={connecting !== null}
              >
                <div className="flex items-center gap-3 w-full">
                  {wallet.icon && (
                    <img 
                      src={wallet.icon} 
                      alt={wallet.name} 
                      className="w-6 h-6 rounded"
                    />
                  )}
                  <span className="flex-1 text-left">{wallet.name}</span>
                  {connecting === wallet.name && (
                    <Loader2 className="w-4 h-4 animate-spin text-emerald" />
                  )}
                </div>
              </Button>
            ))
          ) : (
            <div className="py-4 text-center">
              <p className="text-gray-400 text-sm mb-4">
                No wallet detected. Install one to continue:
              </p>
              <div className="space-y-2">
                {WALLET_INSTALL_LINKS.map((wallet) => (
                  <a
                    key={wallet.name}
                    href={wallet.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-3 rounded-lg bg-[#1A1D23] border border-[#2A2D33] hover:border-emerald transition-colors"
                  >
                    <img src={wallet.icon} alt={wallet.name} className="w-6 h-6 rounded" />
                    <div className="flex-1 text-left">
                      <div className="text-white text-sm font-medium">{wallet.name}</div>
                      <div className="text-gray-500 text-xs">{wallet.description}</div>
                    </div>
                    <ExternalLink className="w-4 h-4 text-gray-500" />
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="pt-2 border-t border-[#2A2D33]">
          <p className="text-xs text-gray-500 text-center">
            Make sure your wallet extension is installed and unlocked
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
