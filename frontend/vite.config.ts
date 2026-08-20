import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // No /api proxy: the frontend calls the Python backend (FastAPI + MCP)
  // directly at its absolute URL (see src/lib/api.ts and chat-api.ts).
});
