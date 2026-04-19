import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#0b1220", 900: "#111827", 700: "#374151", 500: "#6b7280" },
        surface: { DEFAULT: "#0f172a", muted: "#1e293b", card: "#111c2f" },
        accent: { DEFAULT: "#22d3ee", dim: "#0ea5e9" },
      },
    },
  },
  plugins: [],
} satisfies Config;
