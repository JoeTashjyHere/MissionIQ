import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          700: "#1B3957",
          800: "#102A44",
          900: "#0A1F33",
        },
        charcoal: {
          100: "#EEF1F4",
          300: "#C3C7CD",
          500: "#6B7079",
          700: "#3A3F45",
          900: "#1A1D21",
        },
        steel: {
          300: "#A5C0DE",
          500: "#3F7AB8",
          700: "#2A5A8C",
        },
        teal: {
          100: "#E1F1F2",
          500: "#3FA2A6",
          700: "#1E6F73",
        },
        status: {
          green: "#2F7D55",
          greenBg: "#E6F2EB",
          amber: "#B5780C",
          amberBg: "#FBF1DC",
          red: "#A8302E",
          redBg: "#F7E3E2",
          info: "#2A5A8C",
        },
        canvas: "#F6F8FB",
      },
      fontFamily: {
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "monospace",
        ],
      },
      boxShadow: {
        card: "0 1px 2px rgba(10,31,51,0.04), 0 1px 1px rgba(10,31,51,0.06)",
        elevated: "0 12px 32px rgba(10,31,51,0.12)",
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "14px",
      },
      fontSize: {
        eyebrow: ["0.75rem", { lineHeight: "1.2", letterSpacing: "0.08em" }],
        h1: ["1.75rem", { lineHeight: "1.2", fontWeight: "600" }],
        h2: ["1.375rem", { lineHeight: "1.25", fontWeight: "600" }],
        h3: ["1.125rem", { lineHeight: "1.3", fontWeight: "600" }],
      },
    },
  },
  plugins: [],
};

export default config;
