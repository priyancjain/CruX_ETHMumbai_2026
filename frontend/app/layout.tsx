import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/providers";
import ConnectWallet from "@/components/ConnectWallet";

export const metadata: Metadata = {
  title: "AgentScore — Universal Credit Rating for AI Agents",
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

              {/* Logo — new distinctive wordmark */}
              <a href="/" className="flex items-center gap-2.5 group shrink-0">
                {/* Icon mark: stacked bars like a credit score chart */}
                <div className="flex flex-col gap-[3px] w-6 h-6 justify-center">
                  <div className="h-[5px] w-full bg-[#1DB954] rounded-sm" />
                  <div className="h-[5px] w-[70%] bg-[#1DB954]/60 rounded-sm" />
                  <div className="h-[5px] w-[45%] bg-[#1DB954]/30 rounded-sm" />
                </div>
                {/* Wordmark — Space Grotesk avoided per skill, using Sora */}
                <span className="font-display font-black text-lg tracking-[-0.04em] text-gray-900">
                  agent<span className="text-[#1DB954]">score</span>
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
              <span className="font-display font-black text-sm tracking-[-0.04em] text-gray-900">
                agent<span className="text-[#1DB954]">score</span>
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
