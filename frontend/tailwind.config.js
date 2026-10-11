/** @type {import('tailwindcss').Config} */
// Government-portal light theme.
// The app was authored against a dark palette; instead of rewriting every class, the neutral and accent scales are
// re-mapped here so that "dark-UI" classes render as a light, high-contrast (WCAG AA) GIGW-style interface:
//   slate-950 (page) → near-white, slate-400 (muted text on dark) → slate-600 on light, sky-300 (accent text) → blue-700 …
const c = require("tailwindcss/colors");

const invert = (p) => ({
  50: p[950], 100: p[900], 200: p[800], 300: p[700], 400: p[600], 500: p[500],
  600: p[400], 700: p[300], 800: p[200], 900: p[100], 950: p[50],
});
// accents: light "text-X-300/400 on dark" becomes dark text on light; solid fills stay saturated for white text
const accent = (p) => ({
  50: p[50], 100: p[900], 200: p[800], 300: p[700], 400: p[700], 500: p[600],
  600: p[700], 700: p[800], 800: p[200], 900: p[100], 950: p[50],
});
const govBlue = { 50: "#eef4fb", 100: "#d6e4f5", 200: "#adc8ea", 300: "#7ea7db", 400: "#4d82c8", 500: "#2563b0", 600: "#1d4f93",
                  700: "#183f76", 800: "#13325d", 900: "#0f2748", 950: "#0a1a31" };

module.exports = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Noto Sans"', '"Noto Sans Devanagari"', "system-ui", "-apple-system", "Segoe UI", "Roboto", "Arial", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      colors: {
        slate: invert(c.slate), gray: invert(c.gray), zinc: invert(c.zinc), neutral: invert(c.neutral),
        sky: accent(govBlue), blue: accent(govBlue), cyan: accent(c.cyan), indigo: accent(c.indigo), violet: accent(c.violet),
        purple: accent(c.purple), fuchsia: accent(c.fuchsia), emerald: accent(c.emerald), green: accent(c.green), teal: accent(c.teal),
        amber: accent(c.amber), yellow: accent(c.yellow), orange: accent(c.orange), rose: accent(c.rose), red: accent(c.red), lime: accent(c.lime), pink: accent(c.pink),
        ink: { DEFAULT: "#0f2748", soft: "#334155" },
        gov: { navy: "#0f2748", blue: "#1d4f93", sky: "#e8f0fa", line: "#d5deea", saffron: "#ff9933", green: "#138808", gold: "#b7862b" },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
      },
      // Slightly larger small sizes: most of the UI is dense data, and 12px text was too small to read comfortably.
      fontSize: {
        xs: ["0.8125rem", { lineHeight: "1.25rem" }],
        sm: ["0.9375rem", { lineHeight: "1.45rem" }],
      },
      borderRadius: {
        "2xl": "0.625rem",
        xl: "0.5rem",
        lg: "0.375rem",
        md: "0.3rem",
        sm: "0.2rem",
      },
      boxShadow: {
        card: "0 1px 2px rgba(15,39,72,.06), 0 1px 3px rgba(15,39,72,.08)",
        lift: "0 8px 24px -8px rgba(15,39,72,.25)",
      },
    },
  },
  plugins: [],
};
