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
        display: ["Sora", "sans-serif"],
        body:    ["DM Sans", "sans-serif"],
        mono:    ["DM Mono", "monospace"],
      },
      colors: {
        surface: {
          0: "#ffffff",
          1: "#f5f5f5",
          2: "#ebebeb",
          3: "#d6d6d6",
        },
        border: "#e0e0e0",
        accent: {
          DEFAULT: "#1DB954",
          dim:     "rgba(29,185,84,0.12)",
          glow:    "rgba(29,185,84,0.30)",
          dark:    "#17a348",
        },
        danger: {
          DEFAULT: "#FF3B30",
          dim:     "rgba(255,59,48,0.10)",
        },
        signal: {
          blue:   "#007AFF",
          amber:  "#FF9F0A",
          violet: "#5E5CE6",
        },
        tier: {
          S: "#1DB954",
          A: "#5E5CE6",
          B: "#007AFF",
          C: "#FF9F0A",
          D: "#FF3B30",
        },
      },
      boxShadow: {
        glow:      "0 0 0 3px rgba(29,185,84,0.08), 0 8px 32px rgba(0,0,0,0.07)",
        "glow-lg": "0 4px 20px rgba(29,185,84,0.45)",
        card:      "0 1px 3px rgba(0,0,0,0.05), 0 4px 16px rgba(0,0,0,0.04)",
      },
      animation: {
        "fade-in":     "fadeIn 0.45s ease-out forwards",
        "slide-up":    "slideUp 0.4s ease-out forwards",
        "pulse-green": "pulseGreen 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0" },
          to:   { opacity: "1" },
        },
        slideUp: {
          from: { opacity: "0", transform: "translateY(10px)" },
          to:   { opacity: "1", transform: "translateY(0)" },
        },
        pulseGreen: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(29,185,84,0)" },
          "50%":      { boxShadow: "0 0 0 8px rgba(29,185,84,0.12)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
