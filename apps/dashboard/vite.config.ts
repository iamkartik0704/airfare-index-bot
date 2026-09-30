import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

// The dashboard is a pure client of the FastAPI service. In development the
// Vite server proxies the API (and its Swagger docs) so the browser talks to a
// single origin; in production nginx does the same (see nginx.conf).
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.VITE_API_PROXY_TARGET || "http://localhost:8000";
  const proxy = Object.fromEntries(
    ["/api", "/docs", "/openapi.json", "/metrics"].map((path) => [path, { target, changeOrigin: true }]),
  );
  return {
    plugins: [react(), tailwindcss()],
    resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
    server: { port: 5173, proxy },
    preview: { port: 4173, proxy },
    build: {
      sourcemap: true,
      rollupOptions: {
        output: {
          manualChunks: {
            react: ["react", "react-dom", "react-router"],
            charts: ["recharts"],
            query: ["@tanstack/react-query"],
          },
        },
      },
    },
  };
});
