"use client";

import { ReactNode } from "react";
import { PrivyProvider } from "@privy-io/react-auth";
import { AptosWalletAdapterProvider } from "@aptos-labs/wallet-adapter-react";
import { AptosConfig, Network } from "@aptos-labs/ts-sdk";

interface WalletProviderProps {
  children: ReactNode;
}

export function WalletProvider({ children }: WalletProviderProps) {
  // Movement Mainnet configuration
  // Transactions will use their own config based on the connected network
  const aptosConfig = new AptosConfig({
    network: Network.MAINNET,
    fullnode: "https://full.mainnet.movementinfra.xyz/v1",
  });
  
  return (
    <PrivyProvider
      appId={process.env.NEXT_PUBLIC_PRIVY_APP_ID || ""}
      config={{
        loginMethods: ["email", "google", "twitter", "github"],
        appearance: {
          theme: "dark",
          accentColor: "#6366F1",
        },
      }}
    >
      <AptosWalletAdapterProvider
        autoConnect={false}
        dappConfig={aptosConfig}
        onError={(error) => {
          console.error("Wallet error:", JSON.stringify(error, null, 2));
        }}
      >
        {children}
      </AptosWalletAdapterProvider>
    </PrivyProvider>
  );
}

