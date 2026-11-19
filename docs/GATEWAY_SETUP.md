# Pointing a company's AI traffic at Sentry (X22)

Sentry only protects what passes through it. This guide shows three ways to send AI traffic to the gateway, from the simplest to the most complete. The gateway speaks the OpenAI API at `http://<host>:4000/v1`.

## 1. Change two settings in the tool (works today)
Most tools and SDKs read an address and a key:

```bash
export OPENAI_BASE_URL=http://hive.company.internal:4000/v1
export OPENAI_API_KEY=<the person's own key from the Connect page>
```

Each person gets their own key (`POST /v1/keys`, or the Connect page), so every decision is tied to a pseudonym. Python, Node and most IDE plugins need nothing else. For Claude Code use the Anthropic-format endpoint (task G4): `ANTHROPIC_BASE_URL=http://hive.company.internal:4000`.

Rollout tips: give the base URL through the same channel as other developer settings (dotfiles, MDM, devcontainer), start in **shadow mode** (X11) so nobody is blocked in week one, then switch it off when the "would have blocked" numbers look right.

## 2. Force it at the network edge (so nobody can skip step 1)
Block the public AI domains for everyone except the gateway host. The list of domains is `data/ai_tools.csv`. Two common ways:

- **DNS or firewall:** deny the listed domains from user networks, allow them from the gateway host only. People then see the block and use the company chat.
- **Proxy (Squid):** deny the same domains with an ACL and show a custom page that links to the Connect page.

```
# squid.conf (sketch)
acl shadow_ai dstdomain "/etc/squid/ai_domains.txt"
http_access deny shadow_ai
deny_info https://hive.company.internal:3000/connect shadow_ai
```

The access log of that proxy is also what feeds the Shadow AI inventory (O2).

## 3. Inspect content in transit (sketch, not built)
A proxy can pass requests to Sentry before they leave, using ICAP request modification (Squid `icap_service` with `reqmod_precache`). A small ICAP service would take the request body, call `POST /v1/inspect`, and either forward the masked body, return 403, or pass it through. This needs TLS interception, which has legal and privacy consequences (works council, employee notice) and is not part of the hackathon build. Prefer steps 1 and 2.

## For individuals: the paste guard (X21)
`python tools/paste_guard.py` watches the clipboard and offers the masked version of anything sensitive before you paste it into an AI. It is separate from the gateway and needs no network access beyond the brain.

## Check it works
1. Open the Connect page and send the test request: it shows the live status.
2. Send a prompt with a test IBAN from `data/eval/prompts.csv`: the answer carries the `x-dna-decision` header.
3. Look at the incident list: the event appears with a pseudonym, never a name.

## What this does not do
Traffic that never touches the gateway or the proxy is invisible to Sentry: personal phones, home networks, tools with pinned certificates. See `docs/THREAT_MODEL.md`.
