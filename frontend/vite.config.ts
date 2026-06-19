import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During `npm run dev` the API is proxied to the uvicorn backend so the SPA and
// API share an origin (cookies work). In production FastAPI serves the built
// bundle from `dist/`, so no proxy is involved.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8501",
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
