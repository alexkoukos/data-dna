import { defineConfig } from "wxt";

export default defineConfig({
  modules: ["@wxt-dev/module-react"],
  manifest: {
    name: "Hive",
    description: "Checks what you paste into AI chats and keeps company data inside.",
    // IT sets the server and the identity with a Chrome policy (deploy/chrome-policy.json).
    storage: { managed_schema: "managed-schema.json" },
    permissions: ["storage", "sidePanel", "alarms"],
    web_accessible_resources: [
      {
        resources: ["fonts/*.woff2"],
        matches: [
          "https://chatgpt.com/*",
          "https://chat.openai.com/*",
          "https://claude.ai/*",
          "https://gemini.google.com/*",
          "http://localhost/*",
        ],
      },
    ],
    host_permissions: [
      "http://localhost/*",
      "https://chatgpt.com/*",
      "https://chat.openai.com/*",
      "https://claude.ai/*",
      "https://gemini.google.com/*",
    ],
  },
});
