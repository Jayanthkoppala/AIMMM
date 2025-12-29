import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: "#0A0E17",
          card: "#1F2937",
          indigo: "#6366F1",
          purple: "#8B5CF6",
          blue: "#3B82F6",
          green: "#10B981",
          red: "#EF4444",
          amber: "#F59E0B",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      fontSize: {
        hero: ["48px", { lineHeight: "1.1", fontWeight: "800" }],
        "hero-mobile": ["32px", { lineHeight: "1.2", fontWeight: "800" }],
        "page-title": ["32px", { lineHeight: "1.2", fontWeight: "700" }],
        "card-title": ["24px", { lineHeight: "1.3", fontWeight: "600" }],
      },
      boxShadow: {
        glow: "0 0 20px rgba(99, 102, 241, 0.3)",
        "glow-lg": "0 0 40px rgba(99, 102, 241, 0.4)",
        card: "0 4px 6px -1px rgba(0, 0, 0, 0.3)",
        elevated: "0 10px 15px -3px rgba(0, 0, 0, 0.4)",
      },
      backgroundImage: {
        "hero-gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "card-gradient": "linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(139,92,246,0.1) 100%)",
        "button-gradient": "linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%)",
      },
      animation: {
        "pulse-glow": "pulse-glow 2s ease-in-out infinite",
        shimmer: "shimmer 2s infinite",
        float: "float 3s ease-in-out infinite",
      },
      borderRadius: {
        "2xl": "16px",
        "3xl": "24px",
      },
    },
  },
  plugins: [],
};

export default config;
