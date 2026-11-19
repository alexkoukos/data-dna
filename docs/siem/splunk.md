# Splunk example

Send syslog to a Splunk UDP/TCP input (`SIEM_SYSLOG_HOST=<splunk host>`, port 514 or your own).

`inputs.conf`
```
[udp://514]
sourcetype = sentry:cef
index = ai_dlp
```

`props.conf`
```
[sentry:cef]
EXTRACT-cef = CEF:0\|Sentry\|Gate\|[^|]*\|(?<decision>[^|]*)\|[^|]*\|(?<severity>\d+)\|
EXTRACT-user = suser=(?<user_key_id>\S+)
EXTRACT-team = cs1=(?<team>.+?) cs2Label=
EXTRACT-tool = cs2=(?<tool>.+?) cs3Label=
```

Three or more blocks for one user key in 10 minutes:
```
index=ai_dlp sourcetype=sentry:cef decision=block
| bin _time span=10m
| stats count values(tool) AS tools by user_key_id, _time
| where count>=3
```

Pull instead of push: `curl -s "http://brain:8001/v1/export/incidents?since=2026-11-17T09:00:00Z"` into an HTTP Event Collector or a scripted input.
