import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "./" så att den byggda appen fungerar när pywebview öppnar den som fil.
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: { chunkSizeWarningLimit: 1500 }, // three.js är stort, och appen laddas lokalt
  server: {
    port: 5173,
    // I webbläsaren (utan pywebview) går API-anropen till Python-bryggan.
    proxy: { "/api": "http://127.0.0.1:8765" },
  },
});
