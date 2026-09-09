import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import bitrix24UIPluginVite from "@bitrix24/b24ui-nuxt/vite";

export default defineConfig({
  base: "./",
  plugins: [
    vue(),
    bitrix24UIPluginVite({
      colorMode: true,
      colorModeInitialValue: "light",
      colorModeStorageKey: "bitrixvm-color-theme",
    }),
  ],
  resolve: {
    dedupe: ["vue", "vue-router"],
  },
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
});

