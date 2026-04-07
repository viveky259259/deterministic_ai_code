---
name: log-audit
description: Audit the codebase for missing LLM call or prompt logging
---

# Log Audit Skill

Scan the codebase and report any LLM calls or user prompt handlers that are missing required logging.

## Steps
1. Grep for all LLM client call sites (e.g., `client.messages.create`, `openai.chat.completions`)
2. For each call site, verify it has:
   - Pre-call log with request params
   - Post-call log with response metadata and latency
   - Error log in exception handler
3. Grep for all user prompt entry points
4. Verify each has prompt_hash and session_id logging
5. Report findings as a checklist: file:line — status (ok/missing)
