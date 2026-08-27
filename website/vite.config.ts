import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { resolve } from "path";

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "dist",
    rollupOptions: {
      input: {
        index: resolve(__dirname, "index.html"),
        documentation: resolve(__dirname, "documentation.html"),
        console: resolve(__dirname, "console.html"),
      },
    },
  },
});
