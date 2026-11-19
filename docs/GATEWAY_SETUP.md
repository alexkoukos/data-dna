# Pointing a company's AI traffic at Sentry

Sentry only protects what passes through it. This guide shows three ways to send AI traffic to the gateway, from the simplest to the most complete. The gateway speaks the OpenAI API at `http://<host>:4000/v1`.

## 1. Change two settings in the tool (works today)
Most tools and SDKs read an address and a key:

```bash
export OPENAI_BASE_URL=http://sentry.company.internal:4000/v1
export OPENAI_API_KEY=<the person's own key from the Connect page>
```

Each person gets their own key (`POST /v1/keys`, or the Connect page), so every decision is tied to a pseudonym. Python, Node and most IDE plugins need nothing else. For Claude Code use the Anthropic-format endpoint: `ANTHROPIC_BASE_URL=http://sentry.company.internal:4000`.

**What is checked.** The whole request: every earlier turn, the system prompt, tool descriptions and tool results, not only the last message. Answers are checked too, streamed or not (chat, completions, Responses API, Anthropic `/v1/messages`), including reasoning text and tool-call arguments. The person's own masked values are put back in the answer.

**Warnings.** A warning is acknowledged with the header `X-DNA-Ack: <reason>`. The gateway remembers an acknowledgement for 1 hour per personal key: the same earlier text, resent with the same role, is not warned about again (sensitive values in it are still masked, and blocks are never lifted). A changed text warns again, and a gateway restart forgets everything. The master key and keys without a user are shared, so nothing is remembered for them; set the header on every call, for Claude Code with `ANTHROPIC_CUSTOM_HEADERS="X-DNA-Ack: approved by me, reason"`. Trade-off: a tool description acknowledged once stays accepted for an hour, even if it is malicious.

**Limits.** Anthropic signs thinking blocks, so a thinking block we had to change (only when a secret was found in it) fails the signature check if a client replays it. Responses API reasoning summaries and `redacted_thinking` blocks are not covered. Personal keys can call only the inspected routes (chat completions, completions, messages, responses, embeddings, models); other routes answer 401 or 403, and a request that sets `api_base` or other connection settings is refused with 403. The gateway runs as a non-root user (uid 10001) on LiteLLM's image pinned by digest.

**Rollout.** Give the base URL through the same channel as other developer settings (dotfiles, MDM, devcontainer). Start in **shadow mode** so nobody is blocked in week one, then switch it off when the "would have blocked" numbers look right.

## 2. Force it at the network edge (so nobody can skip step 1)
Block the public AI domains for everyone except the gateway host. The list of domains is `data/ai_tools.csv`. Two common ways:

- **DNS or firewall:** deny the listed domains from user networks, allow them from the gateway host only. People then see the block and use the company chat.
- **Proxy (Squid):** deny the same domains with an ACL and show a custom page that links to the Connect page.

```
# squid.conf (sketch)
acl shadow_ai dstdomain "/etc/squid/ai_domains.txt"
http_access deny shadow_ai
deny_info https://sentry.company.internal:3000/connect shadow_ai
```

The access log of that proxy is also what feeds the Shadow AI inventory.

## 3. Inspect content in transit (sketch, not built)
A proxy can pass requests to Sentry before they leave, using ICAP request modification (Squid `icap_service` with `reqmod_precache`). A small ICAP service would take the request body, call `POST /v1/inspect`, and either forward the masked body, return 403, or pass it through. This needs TLS interception, which has legal and privacy consequences (works council, employee notice) and is not part of the hackathon build. Prefer steps 1 and 2.

## For individuals: the paste guard 
`python tools/paste_guard.py` watches the clipboard and offers the masked version of anything sensitive before you paste it into an AI. It is separate from the gateway and needs no network access beyond the brain.

## Check it works
1. Open the Connect page and send the test request: it shows the live status.
2. Send a prompt with a test IBAN from `data/eval/prompts.csv`: the answer carries the `x-dna-decision` header.
3. Look at the incident list: the event appears with a pseudonym, never a name.

## What this does not do
Traffic that never touches the gateway or the proxy is invisible to Sentry: personal phones, home networks, tools with pinned certificates. See `docs/THREAT_MODEL.md`.
