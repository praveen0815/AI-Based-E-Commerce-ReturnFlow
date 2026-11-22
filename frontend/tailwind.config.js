/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          950: "#070B14",
          900: "#0C1424",
          800: "#121C30",
          700: "#1A2740",
          600: "#2A3C5C",
        },
        ink: {
          DEFAULT: "#E7EEF8",
          muted: "#93A4BD",
          faint: "#6D7E98",
        },
      },
      fontFamily: {
        sans: ["Manrope", "Segoe UI", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        panel: "0 24px 60px rgba(0, 0, 0, 0.35)",
      },
    },
  },
  plugins: [],
};
