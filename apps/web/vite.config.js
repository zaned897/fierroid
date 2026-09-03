import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  // El .env vive en la raiz del repo, no en apps/web: un solo archivo de
  // configuracion para API y PWA en vez de dos que se desincronizan.
  envDir: "../..",
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/v1": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});
