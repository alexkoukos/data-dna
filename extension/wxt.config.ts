import { defineConfig } from "wxt";

export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  manifest: {
    name: "Pyli",
    description: "Checks what you paste into AI chats and keeps company data inside.",
    permissions: ["storage", "sidePanel", "alarms"],
    host_permissions: [
      "http://localhost/*",
      "https://chatgpt.com/*",
      "https://chat.openai.com/*",
      "https://claude.ai/*",
      "https://gemini.google.com/*",
    ],
  },
});
