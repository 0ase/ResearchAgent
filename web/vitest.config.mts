import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: [
      { find: "@", replacement: rootDir },
      {
        find: "next-intl/navigation",
        replacement: path.join(rootDir, "test-shims/next-intl-navigation.tsx"),
      },
      {
        find: /^next\/navigation$/,
        replacement: path.join(rootDir, "node_modules/next/navigation.js"),
      },
    ],
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.{test,spec}.{ts,tsx}"],
    exclude: [
      "e2e/**",
      "node_modules/**",
      ".next/**",
      "test-results/**",
      "playwright-report/**",
    ],
    css: true,
  },
});
