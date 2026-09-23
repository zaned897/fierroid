import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  // El .env vive en la raiz del repo, no en apps/web: un solo archivo de
  // configuracion para API y PWA en vez de dos que se desincronizan.
  const envDir = "../..";
  const env = loadEnv(mode, envDir, "");
  const apiTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";

  return {
    envDir,
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/v1": apiTarget,
        "/health": apiTarget,
      },
    },
  };
});
