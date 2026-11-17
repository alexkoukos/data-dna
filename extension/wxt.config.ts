import { defineConfig } from "wxt";

export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  manifest: {
    name: "Pyli",
    // Shown on chrome://extensions, so you can tell which build is loaded.
    version_name: "0.1.0 bee slow-swoop",
    description: "Checks what you paste into AI chats and keeps company data inside.",
    // IT sets the server and the identity with a Chrome policy (deploy/chrome-policy.json).
    storage: { managed_schema: "managed-schema.json" },
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
