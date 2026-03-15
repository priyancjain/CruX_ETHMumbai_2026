"use client";

import { createConfig, http } from "wagmi";
import { base, baseSepolia } from "wagmi/chains";
import { connectorsForWallets } from "@rainbow-me/rainbowkit";
import {
  metaMaskWallet,
  coinbaseWallet,
} from "@rainbow-me/rainbowkit/wallets";



const projectId = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || "73c66f7f2fb486bf97d6205cf145781a";

const getWagmiConfig = () => {
  const connectors = connectorsForWallets(
    [
      {
        groupName: "Recommended",
        wallets: [metaMaskWallet, coinbaseWallet],
      },
    ],
    { 
      appName: "0xTrust", 
      projectId: projectId 
    }
  );

  return createConfig({
    connectors,
    chains: [base, baseSepolia],
    transports: {
      [base.id]: http(),
      [baseSepolia.id]: http("https://sepolia.base.org"),
    },
    ssr: true,
  });
};

// Singleton pattern to avoid re-init during HMR
const globalForWagmi = globalThis as unknown as { wagmiConfig: any };
export const wagmiConfig = globalForWagmi.wagmiConfig || getWagmiConfig();

if (process.env.NODE_ENV !== "production") {
  globalForWagmi.wagmiConfig = wagmiConfig;
}

