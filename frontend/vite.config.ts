import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "/",
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // Keep chart libraries isolated without absorbing their shared React
        // dependencies. Markdown and graph libraries follow their lazy route
        // chunks so their transitive dependencies cannot create chunk cycles.
        onlyExplicitManualChunks: true,
        manualChunks(id) {
          if (id.includes("/node_modules/recharts/")) return "vendor-charts";
        },
      },
    },
  },
});
