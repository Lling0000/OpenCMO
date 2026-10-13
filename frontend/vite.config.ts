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
        // Match only each optional library, rather than absorbing its shared
        // React/ReactDOM dependencies into a vendor chunk needed by the entry.
        onlyExplicitManualChunks: true,
        manualChunks(id) {
          if (/\/node_modules\/(three|react-force-graph-3d|react-force-graph-2d)\//.test(id)) {
            return "vendor-graph";
          }
          if (id.includes("/node_modules/recharts/")) return "vendor-charts";
          if (id.includes("/node_modules/react-markdown/")) return "vendor-markdown";
        },
      },
    },
  },
});
