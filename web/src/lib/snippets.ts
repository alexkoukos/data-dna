/** Copy-paste setup text for each way of connecting a tool. Pure, so it is easy to test. */

export interface Snippet {
  id: string;
  label: string;
  /** Code to copy. Null means this way of connecting is not built yet. */
  code: string | null;
  note: string;
}

export function gatewayUrl(loc: { protocol: string; hostname: string }): string {
  return `${loc.protocol}//${loc.hostname}:4000/v1`;
}

export function buildSnippets(url: string, key: string, model: string): Snippet[] {
  return [
    {
      id: "python",
      label: "OpenAI SDK (Python)",
      note: "Works with the unchanged openai package. Only the address and the key change.",
      code: `from openai import OpenAI

client = OpenAI(base_url="${url}", api_key="${key}")
reply = client.chat.completions.create(
    model="${model}",
    messages=[{"role": "user", "content": "Hello"}],
)
print(reply.choices[0].message.content)`,
    },
    {
      id: "js",
      label: "OpenAI SDK (JavaScript)",
      note: "Works with the unchanged openai package for Node.",
      code: `import OpenAI from "openai";

const client = new OpenAI({ baseURL: "${url}", apiKey: "${key}" });
const reply = await client.chat.completions.create({
  model: "${model}",
  messages: [{ role: "user", content: "Hello" }],
});
console.log(reply.choices[0].message.content);`,
    },
    {
      id: "curl",
      label: "curl",
      note: "Good for a first check from a terminal.",
      code: `curl ${url}/chat/completions \\
  -H "Authorization: Bearer ${key}" \\
  -H "Content-Type: application/json" \\
  -d '{"model": "${model}", "messages": [{"role": "user", "content": "Hello"}]}'`,
    },
    {
      id: "n8n",
      label: "n8n",
      note: "In n8n, add an OpenAI credential with these two values, then use any OpenAI node.",
      code: `Base URL: ${url}
API Key:  ${key}`,
    },
    {
      id: "claude-code",
      label: "Claude Code",
      note: "Not available yet. Claude Code needs an Anthropic-format address, which the gate does not offer in this version.",
      code: null,
    },
    {
      id: "mcp",
      label: "MCP",
      note: "Not available yet. The MCP proxy is planned for a later version.",
      code: null,
    },
  ];
}
