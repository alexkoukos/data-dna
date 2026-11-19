# Sentry browser extension

Personal ChatGPT in the browser bypasses the gateway, so this extension (Chrome or Edge, Manifest V3, plain JavaScript, no build step) checks paste and send on `chatgpt.com` against the gate's own checks before the text leaves the page. It calls `POST /v1/extension/inspect`, `POST /v1/extension/ack` and `GET /v1/extension/me`.

## Load it

1. Open `chrome://extensions`, turn on _Developer mode_, press _Load unpacked_ and choose this folder.
2. Copy the extension ID shown on its card, put it in `.env` as `EXTENSION_ID=...` and run `make up` again. The brain accepts browser calls only from `chrome-extension://<that ID>`.
3. Open the extension's Settings, paste your personal key from the **Connect** page and press Save. The gate address defaults to `http://localhost:8001`.

## What it does

| Decision     | Effect                                                                                               |
| ------------ | ---------------------------------------------------------------------------------------------------- |
| Allow        | Nothing.                                                                                             |
| Mask         | The composer text is replaced with the masked text, with a note naming the entity types and reasons. |
| Warn         | A card with the reasons and _Send anyway_, recorded on the incident like the gateway's `X-DNA-Ack`.  |
| Block, local | The send is stopped; the card offers _Use Company AI_.                                               |

Every non-allow decision is an incident with the tool "ChatGPT (personal)" and channel `browser`, so the Shadow AI view shows it was intercepted. In shadow mode nothing is changed or stopped, only recorded. The user is the owner of the key; the extension never sends a user or team. It stores only the key, the gate address and a daily counter, and makes no network calls except to the gate address.

## Limits

- One site (`chatgpt.com`). Other sites and the desktop and phone apps are not covered, and a person can disable the extension (the proxy and DNS logs still see that).
- Only text is checked: pasted images and file uploads are not.
- If the gate cannot be reached (offline, 502, 503, 504, 429) the extension **fails open**: nothing is blocked, a small badge says so, and nothing is recorded. If the gate refuses to read the text (over 100,000 characters, or malformed) it **fails closed**: "Too long: shorten it or use Company AI".
- ChatGPT changes its page often, so the composer and send-button selectors in `content.js` may need an update. `web/e2e/extension.spec.ts` runs against a saved page, `test/fixture.html`, not the live site.
