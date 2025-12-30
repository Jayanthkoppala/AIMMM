import { useWallet } from "@aptos-labs/wallet-adapter-react";
import {
  Aptos,
  AptosConfig,
  Network,
  AccountAuthenticatorEd25519,
  Ed25519PublicKey,
  Ed25519Signature,
} from "@aptos-labs/ts-sdk";
import { buildAptosLikePaymentHeader } from "x402plus";
import { MOVEMENT_CONFIGS, CURRENT_NETWORK } from "@/app/lib/aptos";

const MOVEMENT_RPC = MOVEMENT_CONFIGS[CURRENT_NETWORK].fullnode;

// Convert wallet's {0: byte, 1: byte, ...} object to Uint8Array
const toBytes = (obj: Record<string, number>) =>
  new Uint8Array(Object.keys(obj).map(Number).sort((a, b) => a - b).map(k => obj[k]));

export function useX402Payment() {
  const { account, signTransaction } = useWallet();

  const payForAccess = async (paymentRequirements: any): Promise<string> => {
    if (!account) throw new Error("Wallet not connected");

    // Build transfer transaction
    // Create Aptos instance only when needed (client-side)
    const aptos = new Aptos(new AptosConfig({ network: Network.CUSTOM, fullnode: MOVEMENT_RPC }));
    const tx = await aptos.transaction.build.simple({
      sender: account.address,
      data: {
        function: "0x1::aptos_account::transfer",
        functionArguments: [paymentRequirements.payTo, paymentRequirements.maxAmountRequired],
      },
    });

    // Sign with wallet
    const signed = await signTransaction({ transactionOrPayload: tx });

    // Extract bytes from wallet's nested response and use SDK classes for BCS serialization
    // Type assertion needed due to SDK type changes - the structure exists at runtime
    const authenticatorData = signed.authenticator as any;
    const pubKeyBytes = toBytes(authenticatorData.public_key?.key?.data || authenticatorData.public_key?.data);
    const sigBytes = toBytes(authenticatorData.signature?.data?.data || authenticatorData.signature?.data);
    const authenticator = new AccountAuthenticatorEd25519(
      new Ed25519PublicKey(pubKeyBytes),
      new Ed25519Signature(sigBytes)
    );

    return buildAptosLikePaymentHeader(paymentRequirements, {
      signatureBcsBase64: Buffer.from(authenticator.bcsToBytes()).toString("base64"),
      transactionBcsBase64: Buffer.from(tx.bcsToBytes()).toString("base64"),
    });
  };

  return { payForAccess, isConnected: !!account };
}

