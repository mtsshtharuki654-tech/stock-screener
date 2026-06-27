import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ma5: "#3b82f6",    // blue-500
        ma20: "#f97316",   // orange-500
        ma60: "#ef4444",   // red-500
      },
    },
  },
  plugins: [],
} satisfies Config;
