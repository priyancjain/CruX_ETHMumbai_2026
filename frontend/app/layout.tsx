import type { Metadata } from "next";
import "./globals.css";
import Providers from "@/components/providers";

export const metadata: Metadata = {
  title: "AgentScore — CIBIL for AI Agents",
  description:
    "Universal credit scoring for autonomous AI agents. Cross-platform ML-powered scoring using onchain behavior.",
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
          {/* Nav */}
          <nav className="sticky top-0 z-50 border-b border-surface-3/60 bg-surface-0/80 backdrop-blur-xl">
            <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
              <a href="/" className="flex items-center gap-2.5 group">
                <div className="w-8 h-8 rounded-lg bg-accent/15 flex items-center justify-center border border-accent/20 group-hover:bg-accent/25 transition-colors">
                  <span className="text-accent font-display font-extrabold text-sm">A</span>
                </div>
                <span className="font-display font-bold text-lg tracking-tight text-white">
                  Agent<span className="text-accent">Score</span>
                </span>
              </a>

              <div className="flex gap-1 items-center">
                <a
                  href="/"
                  className="px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-surface-2/60 transition-all"
                >
                  Browse
                </a>
                <a
                  href="/leaderboard"
                  className="px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-surface-2/60 transition-all"
                >
                  Leaderboard
                </a>
                <a
                  href="/platforms"
                  className="px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-surface-2/60 transition-all"
                >
                  Platforms
                </a>
              </div>
            </div>
          </nav>

          {/* Main */}
          <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
