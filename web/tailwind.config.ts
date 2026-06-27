import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/features/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      colors: {
        // Brand
        brand: {
          50: "#FFF4E6",
          100: "#FFE3BF",
          200: "#FFCC8A",
          300: "#FFB052",
          400: "#FF9526",
          500: "#FF7A00", // primary orange
          600: "#E66A00",
          700: "#B85400",
          800: "#8A3F00",
          900: "#5C2A00",
        },
        sun: {
          400: "#FFD23F",
          500: "#FFB800", // accent yellow
          600: "#E0A100",
        },
        leaf: {
          400: "#4ADE80",
          500: "#22C55E", // accent green / healthy
          600: "#16A34A",
        },
        // Semantic tokens (driven by CSS vars for dark mode)
        background: "hsl(var(--background) / <alpha-value>)",
        foreground: "hsl(var(--foreground) / <alpha-value>)",
        card: "hsl(var(--card) / <alpha-value>)",
        muted: {
          DEFAULT: "hsl(var(--muted) / <alpha-value>)",
          foreground: "hsl(var(--muted-foreground) / <alpha-value>)",
        },
        border: "hsl(var(--border) / <alpha-value>)",
        ring: "hsl(var(--ring) / <alpha-value>)",
        surface: "hsl(var(--surface) / <alpha-value>)",
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
        "3xl": "1.75rem",
        "4xl": "2.25rem",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "var(--font-sans)", "sans-serif"],
      },
      boxShadow: {
        soft: "0 2px 8px -2px rgb(0 0 0 / 0.08), 0 8px 24px -8px rgb(0 0 0 / 0.12)",
        "soft-lg": "0 4px 16px -4px rgb(0 0 0 / 0.10), 0 16px 48px -12px rgb(0 0 0 / 0.18)",
        glow: "0 0 0 1px rgb(255 122 0 / 0.20), 0 8px 32px -8px rgb(255 122 0 / 0.35)",
        "glow-sm": "0 4px 16px -6px rgb(255 122 0 / 0.45)",
        inset: "inset 0 1px 0 0 rgb(255 255 255 / 0.10)",
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #FF7A00 0%, #FFB800 100%)",
        "brand-gradient-soft": "linear-gradient(135deg, rgb(255 122 0 / 0.15) 0%, rgb(255 184 0 / 0.10) 100%)",
        "sunset": "linear-gradient(135deg, #FF7A00 0%, #FF4D6D 60%, #FFB800 100%)",
        "mesh": "radial-gradient(at 20% 20%, rgb(255 122 0 / 0.18) 0px, transparent 50%), radial-gradient(at 80% 0%, rgb(255 184 0 / 0.14) 0px, transparent 50%), radial-gradient(at 80% 80%, rgb(34 197 94 / 0.10) 0px, transparent 50%)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(0.8)", opacity: "0.6" },
          "100%": { transform: "scale(2)", opacity: "0" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-8px)" },
        },
        "gradient-pan": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        blink: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.4s ease forwards",
        "fade-up": "fade-up 0.5s cubic-bezier(0.22, 1, 0.36, 1) forwards",
        shimmer: "shimmer 1.6s infinite",
        "pulse-ring": "pulse-ring 1.8s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        float: "float 6s ease-in-out infinite",
        "gradient-pan": "gradient-pan 6s ease infinite",
        blink: "blink 1s step-end infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
