---
name: heartbeat
description: Produce a concise, honest status heartbeat of running jobs and services (bridges, watchdogs, local servers, long tasks) and flag stalls. Use for "is it still running?", "health check", "status", "where is it stuck?".
---

# Heartbeat

Report live state briefly and truthfully.

## Workflow
1. Identify the components to check (HTTP health endpoints, listening ports,
   named processes, recent log files).
2. Probe each with `bash` (e.g. `Invoke-WebRequest` to a health URL,
   `Get-NetTCPConnection -State Listen`, `Get-CimInstance Win32_Process`).
3. Emit a compact status:
   `component -> up/down/stalled -> evidence (status code, PID, last log line)`.
4. Flag anything stalled (no recent activity) and state why.

## Rules
- Only report what you observed. No fabricated "all good".
- If a probe cannot run, say so.
- Keep it short (table/bullets), one pass.
