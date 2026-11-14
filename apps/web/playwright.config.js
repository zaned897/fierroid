import { defineConfig } from "@playwright/test";
import process from "node:process";

const port = 4178;
const origin = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "./smoke",
  forbidOnly: Boolean(process.env.CI),
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: origin,
    browserName: "chromium",
    reducedMotion: "reduce",
    serviceWorkers: "block",
    timezoneId: "UTC",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `node node_modules/vite/bin/vite.js --mode smoke --host 127.0.0.1 --port ${port} --strictPort`,
    url: origin,
    env: {
      VITE_API_BASE: "",
      VITE_API_PROXY_TARGET: "http://127.0.0.1:1",
    },
  },
});
