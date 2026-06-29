import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/features/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "#1a56db",
          dark: "#0f172a",
          accent: "#f59e0b",
          danger: "#ef4444",
        },
      },
    },
  },
  plugins: [],
};
export default config;
