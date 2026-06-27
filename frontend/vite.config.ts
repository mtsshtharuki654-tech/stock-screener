import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        // SSE streaming requires no timeout and response pass-through
        timeout: 0,
        proxyTimeout: 0,
      },
    },
  },
});
