import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Production URLs: /static/frontend/assets/* (Django STATIC_URL + manifest paths).
// Emit under dist/frontend/assets/ with plain STATICFILES_DIRS (no prefix tuple):
// Django's prefixed dirs use os.sep ("\\" on Windows) but {% static %} paths use "/",
// so FileSystemFinder fails to resolve ("frontend/assets/..." vs "frontend\\assets\\...").
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  base: mode === "production" ? "/static/" : "/",
  build: {
    outDir: "./dist",
    emptyOutDir: true,
    // Keep manifest at frontend/dist/manifest.json.
    manifest: "manifest.json",
    rollupOptions: {
      output: {
        chunkFileNames: "frontend/assets/[name]-[hash].js",
        entryFileNames: "frontend/assets/[name]-[hash].js",
        assetFileNames: "frontend/assets/[name]-[hash][extname]",
        manualChunks(id) {
          if (id.includes("node_modules/@mui")) return "mui";
          if (id.includes("node_modules")) return "vendor";
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      /** All JSON APIs + session auth JSON live under `/api/*` on Django. */
      "/api": "http://127.0.0.1:8000",
      "/login": "http://127.0.0.1:8000",
      "/logout": "http://127.0.0.1:8000",
      "/home": "http://127.0.0.1:8000",
      "/admin": "http://127.0.0.1:8000",
      "/app": "http://127.0.0.1:8000",
      "/static": "http://127.0.0.1:8000",
    },
  },
}));
