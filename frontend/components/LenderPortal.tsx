"use client";

import { useState } from "react";
import { checkLoanEligibility, applyForLoan } from "@/lib/api";
import { useAccount, useSignTypedData } from "wagmi";
import { ConnectButton } from "@rainbow-me/rainbowkit";

export default function LenderPortal({ wallet, score }: { wallet: string; score: any }) {
  const [requestedAmount, setRequestedAmount] = useState<number>(1000);
  const [durationDays, setDurationDays] = useState<number>(30);
  const [eligibility, setEligibility] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [applying, setApplying] = useState(false);
  const [loanResult, setLoanResult] = useState<any>(null);

  const { isConnected, address } = useAccount();
  const { signTypedDataAsync } = useSignTypedData();

  const handleCheckEligibility = async () => {
    setLoading(true);
    try {
      const res = await checkLoanEligibility(wallet, requestedAmount, "USDC");
      setEligibility(res);
      setLoanResult(null);
    } catch (e: any) {
      setEligibility({ error: e.message || "Failed to fetch eligibility" });
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async () => {
    setApplying(true);
    try {
      // 1. Prompt user's wallet to authorize the underwriting via an EIP-712 gas-less signature.
      // Modern DeFi matching engines use signed intents (off-chain) rather than raw transfers to prevent upfront gas costs.
      await signTypedDataAsync({
        domain: {
          name: "0xTrust Protocol",
          version: "1",
          chainId: 8453, // Base Mainnet
        },
        types: {
          LoanUnderwriting: [
            { name: "agentWallet", type: "address" },
            { name: "loanAmountUSDC", type: "uint256" },
            { name: "durationDays", type: "uint256" },
            { name: "interestRateBps", type: "uint256" },
          ],
        },
        primaryType: "LoanUnderwriting",
        message: {
          agentWallet: wallet as `0x${string}`,
          // USDC has 6 decimals, so multiply the raw amount by 10^6 for realism
          loanAmountUSDC: BigInt(requestedAmount * 1_000_000), 
          durationDays: BigInt(durationDays),
          interestRateBps: BigInt(eligibility.interest_rate_bps),
        },
      });

      // 2. Once signature succeeds in wallet, hit backend to register the active loan
      const res = await applyForLoan(wallet, requestedAmount, durationDays, "USDC");
      setLoanResult(res);
    } catch (e: any) {
      const userRejected = e.message?.includes("User rejected") || e.message?.includes("rejected the request");
      setLoanResult({ 
        approved: false, 
        message: userRejected ? "Transaction rejected by user." : (e.message || "Loan application failed.") 
      });
    } finally {
      setApplying(false);
    }
  };

  return (
    <div className="glass-card p-6 mt-6 space-y-6">
      <h2 className="text-xl font-display font-bold text-white border-b border-surface-3/30 pb-3">
        DeFi Lender Underwriting
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <p className="text-sm text-slate-400">
            Simulate a DeFi protocol using the 0xTrust API to underwrite and issue a loan continuously based on {wallet.slice(0, 6)}... profile.
          </p>

          <div className="space-y-4 pt-2">
            <div>
              <label className="block text-[10px] uppercase font-mono text-slate-500 mb-2">Requested Amount (USDC)</label>
              <input
                type="number"
                value={requestedAmount}
                onChange={(e) => setRequestedAmount(Number(e.target.value))}
                className="w-full bg-surface-2 border border-surface-3 rounded-lg px-4 py-2 font-mono text-white focus:border-accent outline-none"
              />
            </div>
            <div>
              <label className="block text-[10px] uppercase font-mono text-slate-500 mb-2">Duration (Days)</label>
              <input
                type="number"
                value={durationDays}
                onChange={(e) => setDurationDays(Number(e.target.value))}
                className="w-full bg-surface-2 border border-surface-3 rounded-lg px-4 py-2 font-mono text-white focus:border-accent outline-none"
              />
            </div>

            <button
              onClick={handleCheckEligibility}
              disabled={loading}
              className="w-full py-3 bg-accent/20 hover:bg-accent/30 disabled:opacity-50 text-accent font-bold rounded-xl transition-all"
            >
              {loading ? "CHECKING..." : "CHECK ELIGIBILITY"}
            </button>
          </div>
        </div>

        <div className="space-y-4 border-l border-surface-3/30 pl-6">
          <h3 className="text-sm font-bold text-slate-300">Underwriting Result</h3>
          
          {!eligibility && !loanResult && (
            <div className="bg-surface-2/30 rounded-lg p-6 flex items-center justify-center text-slate-500 font-mono text-xs border border-surface-3/20 h-full">
              Run eligibility check
            </div>
          )}

          {eligibility && !loanResult && (
            <div className={`rounded-xl p-5 border ${eligibility.eligible ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
              <div className="flex items-center gap-3 mb-4">
                <div className={`w-3 h-3 rounded-full ${eligibility.eligible ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="font-bold text-white uppercase text-sm">{eligibility.eligible ? 'Eligible' : 'Rejected'}</span>
              </div>
              
              <p className="text-slate-300 text-sm mb-4">{eligibility.reason || eligibility.error}</p>

              {eligibility.eligible && (
                <>
                  <div className="grid grid-cols-2 gap-4 mb-5">
                    <div className="bg-surface-1 rounded-lg p-3 border border-surface-3/40">
                      <p className="text-[10px] font-mono text-slate-500">MAX AMOUNT</p>
                      <p className="font-mono text-white mt-1">${eligibility.max_loan_amount}</p>
                    </div>
                    <div className="bg-surface-1 rounded-lg p-3 border border-surface-3/40">
                      <p className="text-[10px] font-mono text-slate-500">INTEREST RATE</p>
                      <p className="font-mono text-white mt-1">{eligibility.interest_rate_bps / 100}% APR</p>
                    </div>
                  </div>

                  {!isConnected ? (
                    <div className="mt-4 flex flex-col items-center p-4 bg-surface-1 rounded-xl border border-surface-3/40">
                      <p className="text-xs text-slate-400 font-mono mb-3 uppercase tracking-wider">Connect wallet to authorize loan</p>
                      <ConnectButton />
                    </div>
                  ) : (
                    <button
                      onClick={handleApply}
                      disabled={applying}
                      className="w-full py-3 bg-green-500/20 hover:bg-green-500/30 text-green-400 font-bold rounded-xl transition-all"
                    >
                      {applying ? "ISSUING LOAN..." : "AUTHORIZE & ISSUE LOAN"}
                    </button>
                  )}
                </>
              )}
            </div>
          )}

          {loanResult && (
            <div className={`rounded-xl p-5 border ${loanResult.approved ? 'bg-green-500/20 border-green-500/50' : 'bg-red-500/10 border-red-500/30'}`}>
              <h4 className={`font-bold mb-2 ${loanResult.approved ? 'text-green-400' : 'text-red-400'}`}>
                {loanResult.approved ? "Loan Funded Successfully!" : "Loan Application Denied"}
              </h4>
              <p className="text-sm text-slate-300 mb-4">{loanResult.message}</p>
              {loanResult.approved && (
                <div className="bg-surface-1 border border-surface-3/50 rounded-lg p-3 text-xs font-mono text-slate-400 space-y-1">
                  <p>Loan ID: <span className="text-white">{loanResult.loan_id.slice(0, 8)}...</span></p>
                  <p>Amount: <span className="text-white">${loanResult.amount} USDC</span></p>
                  <p>Interest: <span className="text-white">{loanResult.interest_rate_bps / 100}%</span></p>
                  <p>Status: <span className="text-green-400">{loanResult.status.toUpperCase()}</span></p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
