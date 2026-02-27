import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        slateblue: "#6F8FAF",
        charcoal: "#0d1118",
        panel: "#141c29",
        accent: "#35c2b6",
        amberish: "#f5b84d",
        rosealert: "#ff5f6d"
      },
      boxShadow: {
        panel: "0 12px 28px rgba(6, 12, 20, 0.45)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        rise: "rise 420ms ease-out forwards",
      },
    },
  },
  plugins: [],
};

export default config;
