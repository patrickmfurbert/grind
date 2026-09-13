import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 3001, proxy: { "/api": "http://localhost:8001" } },
  preview: {
    host: "127.0.0.1",
    port: 3001,
    // Requests arrive via nginx with the Tailscale hostname as the Host header;
    // Vite's default host check would otherwise reject them as DNS rebinding.
    allowedHosts: ["hp-z420-mint-steve", "grind.hp-z420-mint-steve", "localhost"],
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.jsx"],
    globals: true,
  },
});
