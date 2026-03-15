import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/providers";
import ConnectWallet from "@/components/ConnectWallet";

export const metadata: Metadata = {
  title: "0xTrust — Universal Credit Rating for AI Agents",
  description:
    "The CIBIL for autonomous AI agents. Cross-platform on-chain credit scoring, underwriting, and DeFi lending.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Providers>

          {/* ── Ticker bar — CENTERED ── */}
          <div className="bg-[#0a0a0a] border-b border-[#1a1a1a] overflow-hidden">
            <div className="flex items-center justify-center gap-6 px-6 py-1.5 flex-wrap">
              {[
                { label: "VIRTUALS", val: "21,171", color: "text-green-400" },
                { label: "OLAS", val: "9,000", color: "text-blue-400" },
                { label: "FETCH.AI", val: "10,000", color: "text-yellow-400" },
                { label: "AVG SCORE", val: "480/1000", color: "text-green-400" },
                { label: "NETWORK", val: "BASE", color: "text-cyan-400" },
              ].map((item, i) => (
                <span key={item.label} className="flex items-center gap-1.5 text-[10px] font-mono whitespace-nowrap">
                  <span className="text-gray-500">{item.label}</span>
                  <span className={`${item.color} font-semibold`}>{item.val}</span>
                  {i < 4 && <span className="text-gray-700 ml-2">·</span>}
                </span>
              ))}
            </div>
          </div>

          {/* ── Main navbar ── */}
          <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-xl border-b border-[#e0e0e0] shadow-sm">
            <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">

              {/* Logo — new 0xTrust branding */}
              <a href="/" className="flex items-center gap-2.5 group shrink-0">
                {/* Icon mark: simplified shield with cross from 0xTrust logo */}
                <div className="relative w-6 h-6 flex items-center justify-center">
                  <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full text-[#1DB954]">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M8 8l8 8M16 8l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                </div>
                {/* Wordmark */}
                <span className="font-display font-black text-xl tracking-[-0.04em] text-gray-900">
                  <span className="text-[#1DB954]">0x</span>Trust.
                </span>
              </a>

              {/* Center nav links */}
              <div className="absolute left-1/2 -translate-x-1/2 flex gap-0.5 items-center">
                {[
                  { href: "/", label: "Browse" },
                  { href: "/leaderboard", label: "Leaderboard" },
                  { href: "/platforms", label: "Platforms" },
                ].map((link) => (
                  <a
                    key={link.href}
                    href={link.href}
                    className="px-4 py-2 rounded-lg text-sm font-body font-medium text-gray-500
                      hover:text-gray-900 hover:bg-gray-100 transition-all"
                  >
                    {link.label}
                  </a>
                ))}
              </div>

              {/* Right — live dot + wallet */}
              <div className="flex items-center gap-3 shrink-0">
                <div className="hidden md:flex items-center gap-1.5 text-[11px] font-mono text-gray-400 bg-gray-100 px-3 py-1.5 rounded-full">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#1DB954] animate-pulse" />
                  BASE
                </div>
                <ConnectWallet />
              </div>

            </div>
          </nav>

          {/* ── Main content ── */}
          <main className="max-w-7xl mx-auto px-6 py-10">{children}</main>

          {/* ── Footer ── */}
          <footer className="border-t border-[#e0e0e0] mt-20 py-8">
            <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
              <span className="font-display font-black text-lg tracking-[-0.04em] text-gray-900">
                <span className="text-[#1DB954]">0x</span>Trust.
              </span>
              <p className="text-xs font-mono text-gray-400">
                ETH Mumbai 2026 · Universal Credit Rating for AI Agents
              </p>
            </div>
          </footer>
        </Providers>
      </body>
    </html>
  );
}
