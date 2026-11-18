# Pointing a company's AI traffic at Pyli (X22)

Pyli only protects what passes through it. This guide shows three ways to send AI traffic to the gateway, from the simplest to the most complete. The gateway speaks the OpenAI API at `http://<host>:4000/v1`.

## 1. Change two settings in the tool (works today)
Most tools and SDKs read an address and a key:

```bash
export OPENAI_BASE_URL=http://pyli.company.internal:4000/v1
export OPENAI_API_KEY=<the person's own key from the Connect page>
```

Each person gets their own key (`POST /v1/keys`, or the Connect page), so every decision is tied to a pseudonym. Python, Node and most IDE plugins need nothing else. For Claude Code use the Anthropic-format endpoint (task G4): `ANTHROPIC_BASE_URL=http://pyli.company.internal:4000`.

The gateway checks the whole request: every earlier turn, the system prompt or instructions, tool descriptions and tool results, not only the last message. Tools that resend the full conversation on every call (Claude Code, API clients) are checked again each time, but a warning you acknowledged once (with `X-DNA-Ack`) is remembered by the gateway for 1 hour, per personal key: the same earlier text, sent again with the same role, is no longer warned about (sensitive values in it are still masked, and blocks are never lifted). A changed text is a new text and warns again; a restart of the gateway forgets everything. The master key and keys without a user are shared by many people, so nothing is remembered for them: those clients still need to send `X-DNA-Ack` on every call, for Claude Code via `ANTHROPIC_CUSTOM_HEADERS="X-DNA-Ack: approved by me, reason"`. Trade-off: a tool description you acknowledged stays accepted for 1 hour, even if it is malicious; change of its text brings the warning back.

Streamed answers are filtered too: chat, text completion, Responses API and Anthropic `/v1/messages` streams are collected, checked once, and sent with the cleaned text in the first content event (the client still gets a normal stream, the text just arrives together). Not covered: reasoning summaries, function-call arguments and annotations in streamed Responses answers.

A client that sends `organization` (the OpenAI SDK does, as a header or in the body) is accepted: the gateway drops the body field and does not forward the header. Other connection settings (`api_key`, `api_base`, `base_url`, `extra_headers`...) are still refused with 403.

Rollout tips: give the base URL through the same channel as other developer settings (dotfiles, MDM, devcontainer), start in **shadow mode** (X11) so nobody is blocked in week one, then switch it off when the "would have blocked" numbers look right.

## 2. Force it at the network edge (so nobody can skip step 1)
Block the public AI domains for everyone except the gateway host. The list of domains is `data/ai_tools.csv`. Two common ways:

- **DNS or firewall:** deny the listed domains from user networks, allow them from the gateway host only. People then see the block and use the company chat.
- **Proxy (Squid):** deny the same domains with an ACL and show a custom page that links to the Connect page.

```
# squid.conf (sketch)
acl shadow_ai dstdomain "/etc/squid/ai_domains.txt"
http_access deny shadow_ai
deny_info https://pyli.company.internal:3000/connect shadow_ai
```

The access log of that proxy is also what feeds the Shadow AI inventory (O2).

## 3. Inspect content in transit (sketch, not built)
A proxy can pass requests to Pyli before they leave, using ICAP request modification (Squid `icap_service` with `reqmod_precache`). A small ICAP service would take the request body, call `POST /v1/inspect`, and either forward the masked body, return 403, or pass it through. This needs TLS interception, which has legal and privacy consequences (works council, employee notice) and is not part of the hackathon build. Prefer steps 1 and 2.

## For individuals: the paste guard (X21)
`python tools/paste_guard.py` watches the clipboard and offers the masked version of anything sensitive before you paste it into an AI. It is separate from the gateway and needs no network access beyond the brain.

## Check it works
1. Open the Connect page and send the test request: it shows the live status.
2. Send a prompt with a test IBAN from `data/eval/prompts.csv`: the answer carries the `x-dna-decision` header.
3. Look at the incident list: the event appears with a pseudonym, never a name.

## What this does not do
Traffic that never touches the gateway or the proxy is invisible to Pyli: personal phones, home networks, tools with pinned certificates. See `docs/THREAT_MODEL.md`.
