# Elastic example

**Webhook or pull:** post the JSON lines to an ingest pipeline (they are already one event per line).

```
curl -s "http://brain:8001/v1/export/incidents?since=2026-11-17T09:00:00Z" \
  | curl -s -XPOST "https://es:9200/sentry-incidents/_bulk" -H 'Content-Type: application/x-ndjson' \
      --data-binary @<(awk '{print "{\"index\":{}}"; print}')
```

**Syslog:** use the Elastic Agent CEF integration (UDP 514). Fields land as `source.user.name` (key ID), `event.action` (decision), `cs1`..`cs4`.

Three or more blocks for one user key in 10 minutes (a threshold detection rule, KQL, group by `user_key_id`, threshold 3, window 10m):
```
decision : "block"
```
Or ES|QL:
```
FROM sentry-incidents
| WHERE decision == "block" AND @timestamp > NOW() - 10 minutes
| STATS blocks = COUNT(*) BY user_key_id
| WHERE blocks >= 3
```
