import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, the dashboard runs on Vite and the API on :8000; these proxies forward the API
// paths (and the WebSocket) so the browser talks to one origin, as it does in production
// where FastAPI serves the built dashboard.
const API = "http://localhost:8000";
const apiPaths = ["/scan", "/check_action", "/incidents", "/events", "/approvals", "/policy", "/stats", "/results", "/health"];

export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // reachable from phones and tablets on the same network
    proxy: {
      ...Object.fromEntries(apiPaths.map((path) => [path, { target: API, changeOrigin: true }])),
      "/ws": { target: API.replace("http", "ws"), ws: true },
    },
  },
});
