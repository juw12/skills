---
name: memory-management
description: Capture and retrieve durable project memory (decisions, lessons learned, context) in the Obsidian vault / docs so it survives across sessions. Use to "remember", "recall", "save this decision", "what did we decide about X".
---

# Memory Management

Keep durable, accurate memory. Facts only.

## Storage
- Obsidian vault: your Obsidian vault (default `~/Documents/Obsidian Vault`; set `OBSIDIAN_VAULT` to override) (and project `docs/`).
- Access: prefer the `obsidian` MCP tools; if they are NOT loaded, use the Local
  REST API directly (see `AGENTS.md`): `GET/PUT/POST https://127.0.0.1:27124/vault/<path>`
  with header `Authorization: Bearer <OBSIDIAN_API_KEY>` (disable TLS verify).
  Requires Obsidian open with the "Local REST API" plugin enabled.

## Remember
1. Write a concise, dated note (decision / lesson / context) with a clear title.
2. Link related notes. Prefer appending over duplicates.
3. Never store secrets, credentials, or personal/sensitive data.

## Recall
1. Search the vault; return relevant notes with their paths.
2. Summarize faithfully and quote the source. If nothing is found, say so.

## Rules
- No invented memories. Note uncertainty explicitly.
