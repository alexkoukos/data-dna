# Sentry browser extension

Personal ChatGPT, Claude and Gemini tabs bypass the gateway, so this extension (Chrome, Edge, Brave; Manifest V3; TypeScript with [WXT](https://wxt.dev)) checks paste, send and file attach on those sites before anything leaves the page.

## Load it

```bash
make extension-zip
```

Open `chrome://extensions`, turn on _Developer mode_, press _Load unpacked_ and choose `extension/.output/chrome-mv3` (or unzip `sentry-extension.zip`). The dashboard also serves the zip from its _Get the extension_ page.

It connects by itself: on install the worker (`entrypoints/background.ts`) pairs with `http://localhost:8001` as the first demo person and retries every minute until the server is up. The popup shows "Connected as …" or a "Not connected" card with a _Connect_ button. Tabs that were already open on an AI site are protected straight away. IT can set the server address and other settings with a Chrome policy (`deploy/chrome-policy.json`, see [deploy/README.md](../deploy/README.md)).

## How a check runs

1. **In the browser** (`src/check.ts`, `src/detect/`), with no network: the same rules the brain uses for identifiers, secrets and client names (`shared/fixtures/l1.json`).
2. **On the company server**: `POST /v1/check` runs the full brain pipeline (documents, session memory, injection, files). The stricter of the two answers wins.
3. If the server does not answer within 400 ms, the policy's fail mode decides for each category: some kinds of content are blocked until they can be checked, the rest go through.

| Outcome          | What the person sees                                                                                                       |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Allowed          | Nothing.                                                                                                                   |
| Masked           | The values are replaced in the composer (`[IBAN_1]`), and restored in the answer on the page.                              |
| Warned           | A card with the reasons and _Send anyway_.                                                                                 |
| Answered locally | The send is stopped; _Ask the company AI_ opens the side panel, where the company's local model answers (`/v1/ask-local`). |
| Blocked          | A card with the reason and _Open company AI_. A stopped file offers _Upload it in Company AI_, which opens `/chat`.        |

The extension also fetches the policy (`/v1/policy`, with ETag) and sends counts of what it saw (`/v1/events`, never text), which feed the Shadow AI view. Text over 100,000 characters and files over about 20 MB are refused before sending.

## Code

- `entrypoints/`: the worker, the content script for the AI sites, the popup, the side panel (Company AI) and the options page.
- `src/adapters/`: one adapter per site (`chatgpt.ts`, `claude.ts`, `gemini.ts`, and `mock.ts` for the local test page).
- `src/check.ts`, `src/detect/`: the in-browser check; `src/api.ts`: calls to the brain.

## Test

```bash
npm test                          # unit tests (vitest)
node --test test/logic.test.mjs   # shared rules
npm run e2e                       # Playwright, needs `make up`
```

## Limits

- Only the three sites above. Desktop and phone apps are not covered, and a person can turn the extension off (the proxy and DNS logs still see the traffic).
- AI sites change their pages often, so the selectors in `src/adapters/` may need an update. The e2e tests run against a local mock page, not the live sites.
