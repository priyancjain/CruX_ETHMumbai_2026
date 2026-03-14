import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ["Syne", "sans-serif"],
        body: ["IBM Plex Sans", "sans-serif"],
        mono: ["IBM Plex Mono", "monospace"],
      },
      colors: {
        surface: {
          0: "#04060e",
          1: "#0a0e1a",
          2: "#111827",
          3: "#1a2236",
        },
        accent: {
          DEFAULT: "#06d6a0",
          dim: "#06d6a040",
          glow: "#06d6a080",
        },
        tier: {
          S: "#06d6a0",
          A: "#34d399",
          B: "#60a5fa",
          C: "#fbbf24",
          D: "#f87171",
        },
      },
      boxShadow: {
        glow: "0 0 20px rgba(6, 214, 160, 0.15)",
        "glow-lg": "0 0 40px rgba(6, 214, 160, 0.2)",
      },
      animation: {
        "fade-in": "fadeIn 0.6s ease-out forwards",
        "slide-up": "slideUp 0.5s ease-out forwards",
        "pulse-glow": "pulseGlow 3s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(16px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 20px rgba(6, 214, 160, 0.1)" },
          "50%": { boxShadow: "0 0 40px rgba(6, 214, 160, 0.25)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
