# Sending Sentry incidents to the SOC

"How does this reach our SOC?" Three ways, all optional, none sends prompt text.

| Way | Turn it on | Format |
|---|---|---|
| Pull | `GET /v1/export/incidents?since=2026-11-17T09:00:00Z` | JSON lines, oldest first |
| Syslog push | `SIEM_SYSLOG_HOST`, `SIEM_SYSLOG_PORT` (514), `SIEM_SYSLOG_PROTO` (`udp` or `tcp`) | CEF in a syslog frame (facility local0) |
| Webhook push | `SIEM_WEBHOOK_URL`, `SIEM_WEBHOOK_SECRET` | JSON body, header `X-Sentry-Signature: sha256=<HMAC-SHA256 of the body>` |

Set the variables in `.env` (see `.env.example`) and run `docker compose up -d brain`. Set `SIEM_EXPORT_TOKEN` to require `Authorization: Bearer <token>` on the export.

## What is in an event

`id`, `time`, `user_key_id`, `team`, `tool`, `decision`, `categories`, `document_id`, `rule_ids`, `shadow`.

- `user_key_id` is the pseudonym (for example `u-de036ece`), never the name. Learning who it is still needs the two-person reveal in the Security area.
- `rule_ids` are the detection layers that fired, for example `patterns-and-checksums`, `document-matching`.
- **No prompt text, no masked preview and no free-text reasons**, by construction: an event is built from the named fields above and nothing else (`services/brain/src/brain/siem.py`, tested in `test_x30_siem.py`).
- Only incidents are sent (mask, warn, local, block, rerouted). Allowed prompts are not.

Example JSON line:

```json
{"id":42,"time":"2026-11-17T10:30:00+00:00","user_key_id":"u-de036ece","team":"Finance","tool":"ChatGPT (personal)","decision":"block","categories":["document","iban"],"document_id":3,"rule_ids":["document-matching","patterns-and-checksums"],"shadow":false}
```

The same event as CEF (the one line, split here for reading):

```
CEF:0|Sentry|Gate|1.0|block|Sentry block: ChatGPT (personal)|8|rt=1795084200000 externalId=42 suser=u-de036ece act=block
  cs1Label=team cs1=Finance cs2Label=tool cs2=ChatGPT (personal) cs3Label=categories cs3=document,iban
  cs4Label=ruleIds cs4=document-matching,patterns-and-checksums cn1Label=documentId cn1=3 cn2Label=shadow cn2=0
```

Severity: block 8, local 6, warn 5, rerouted 4, mask 3. A `rerouted` event is sent when someone sends a stopped message to Company AI instead.

## Verifying a webhook

```python
import hmac, hashlib
def ok(body: bytes, header: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))
```

Sign and compare the exact bytes you received, not a re-encoded copy.

## Demo: watch events arrive

1. Add `SIEM_SYSLOG_HOST=syslog-receiver` to `.env`.
2. `make siem` starts a tiny receiver (compose profile `siem`) and follows its log.
3. Send a risky message in the Company AI chat (or run `make simulate`): a `CEF:0|Sentry|Gate|...` line appears within a second. Practice on `/break-it` creates no incident, so it sends nothing.

## Detection rules and searches

- `sigma/sentry-repeated-blocks.yml`: three or more blocks by one user key in 10 minutes.
- `splunk.md` and `elastic.md`: how to ingest the CEF lines and the same search in SPL and Elasticsearch.
