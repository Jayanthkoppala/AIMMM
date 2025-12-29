"use client";

import { ReactNode } from "react";
import { PrivyProvider } from "@privy-io/react-auth";
import { AptosWalletAdapterProvider } from "@aptos-labs/wallet-adapter-react";
import { AptosConfig, Network } from "@aptos-labs/ts-sdk";

interface WalletProviderProps {
  children: ReactNode;
}

export function WalletProvider({ children }: WalletProviderProps) {
  const privyAppId = process.env.NEXT_PUBLIC_PRIVY_APP_ID;
  
  const aptosConfig = new AptosConfig({
    network: Network.MAINNET,
    fullnode: "https://full.mainnet.movementinfra.xyz/v1",
  });

  const aptosWrapper = (
    <AptosWalletAdapterProvider
      autoConnect={false}
      dappConfig={aptosConfig}
      onError={(error) => {
        console.error("Wallet error:", JSON.stringify(error, null, 2));
      }}
    >
      {children}
    </AptosWalletAdapterProvider>
  );

  if (!privyAppId) {
    return aptosWrapper;
  }
  
  return (
    <PrivyProvider
      appId={privyAppId}
      config={{
        loginMethods: ["email", "google", "twitter", "github"],
        appearance: {
          theme: "dark",
          accentColor: "#1FAA68",
        },
        embeddedWallets: {
          ethereum: {
            createOnLogin: "users-without-wallets",
          },
        },
      }}
    >
      {aptosWrapper}
    </PrivyProvider>
  );
}

