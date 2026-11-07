import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          50: "#eef0ff",
          100: "#e0e3ff",
          200: "#c6ccff",
          300: "#a3aaff",
          400: "#7f82fa",
          500: "#635bff",
          600: "#5147e6",
          700: "#433ac0",
          800: "#38329b",
          900: "#2f2b7a",
        },
        ink: {
          900: "#0f1115",
          700: "#2a2f3a",
          500: "#5b6472",
          400: "#8a93a3",
        },
        canvas: "#f6f7f9",
      },
      boxShadow: {
        card: "0 1px 2px rgba(16,18,27,0.04), 0 8px 24px rgba(16,18,27,0.06)",
        soft: "0 1px 3px rgba(16,18,27,0.06)",
      },
      borderRadius: {
        xl: "14px",
        "2xl": "18px",
      },
    },
  },
  plugins: [],
};
export default config;
