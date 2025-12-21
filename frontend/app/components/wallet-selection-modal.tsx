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
import { getAptosWallets } from "@aptos-labs/wallet-standard";

interface WalletSelectionModalProps {
  children: React.ReactNode;
}

export function WalletSelectionModal({ children }: WalletSelectionModalProps) {
  const [open, setOpen] = useState(false);
  const { wallets, connect } = useWallet();

  // Filter out unwanted wallets, remove duplicates, and sort with Nightly first
  const filteredWallets = wallets
    .filter((wallet) => {
      const name = wallet.name.toLowerCase();
      return !name.includes("petra") && 
             !name.includes("google") && 
             !name.includes("apple");
    })
    .filter((wallet, index, self) => {
      // Remove duplicates based on wallet name
      return index === self.findIndex((w) => w.name === wallet.name);
    })
    .sort((a, b) => {
      // Nightly always first
      if (a.name.toLowerCase().includes("nightly")) return -1;
      if (b.name.toLowerCase().includes("nightly")) return 1;
      return 0;
    });

  const handleWalletSelect = async (walletName: string) => {
    try {
      // Try to connect with Movement network info using wallet-standard features
      if (typeof window !== "undefined") {
        const allWallets = getAptosWallets();
        const selectedWallet = allWallets.aptosWallets.find(w => w.name === walletName);
        
        if (selectedWallet?.features?.['aptos:connect']) {
          // Use wallet-standard aptos:connect feature with network info
          const networkInfo: any = {
            chainId: 126, // Movement Mainnet
            name: "custom",
            url: "https://full.mainnet.movementinfra.xyz/v1"
          };
          
          try {
            const result = await selectedWallet.features['aptos:connect'].connect(false, networkInfo);
            
            // If wallet-standard connection succeeded, now connect via wallet adapter
            if (result.status === "Approved") {
              await connect(walletName);
              setOpen(false);
              return;
            }
          } catch (connectError) {
            // Fallback to standard connection
          }
        }
      }
      
      // Fallback to standard wallet adapter connection
      await connect(walletName);
      setOpen(false);
    } catch (error) {
      // Silent error - wallet adapter will handle error display
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {children}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Connect Wallet</DialogTitle>
          <DialogDescription>
            Choose a wallet to connect to Movement Network
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          {filteredWallets.length === 0 ? (
            <p className="text-center text-muted-foreground py-4">
              No compatible wallets detected. Please install a supported wallet.
            </p>
          ) : (
            filteredWallets.map((wallet) => (
              <Button
                key={wallet.name}
                variant="outline"
                className="w-full justify-start h-12"
                onClick={() => handleWalletSelect(wallet.name)}
              >
                <div className="flex items-center space-x-3">
                  {wallet.icon && (
                    <img 
                      src={wallet.icon} 
                      alt={wallet.name} 
                      className="w-6 h-6"
                    />
                  )}
                  <span>{wallet.name}</span>
                </div>
              </Button>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

