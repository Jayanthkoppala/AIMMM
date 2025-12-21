// Movement network configurations (can be used server-side)
export const MOVEMENT_CONFIGS = {
  mainnet: {
    chainId: 126,
    name: "Movement Mainnet",
    fullnode: "https://full.mainnet.movementinfra.xyz/v1",
    explorer: "mainnet"
  },
  testnet: {
    chainId: 250,
    name: "Movement Testnet",
    fullnode: "https://testnet.movementnetwork.xyz/v1",
    explorer: "testnet"
  }
};

// Current network (change this to switch between mainnet/testnet)
export const CURRENT_NETWORK = 'testnet' as keyof typeof MOVEMENT_CONFIGS;

// Get explorer URL based on current network (works server-side)
export const getExplorerUrl = (txHash: string): string => {
  // Ensure txHash starts with 0x
  const formattedHash = txHash.startsWith('0x') ? txHash : `0x${txHash}`;
  const network = MOVEMENT_CONFIGS[CURRENT_NETWORK].explorer;
  return `https://explorer.movementnetwork.xyz/txn/${formattedHash}?network=${network}`;
};

// Utility to convert Uint8Array to hex string
export const toHex = (buffer: Uint8Array): string => {
  return Array.from(buffer)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
};

