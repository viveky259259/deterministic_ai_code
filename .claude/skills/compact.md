---
name: compact
description: Compact the current conversation context — summarize and trim to essential state
---

# Compact Skill

Trigger this when context usage approaches 40%.

## What to Preserve
- Current task description and acceptance criteria
- Key architectural decisions made in this session
- File paths currently being edited and their purpose
- Test results (pass/fail counts, specific failures)
- Unresolved blockers or open questions

## What to Discard
- Verbose tool output already acted upon
- Exploration of dead-end approaches
- Repeated file reads of the same content
- Intermediate drafts that were superseded

## Steps
1. Summarize the conversation so far in <10 bullet points
2. List all files modified with one-line descriptions
3. Note any pending tasks or decisions
4. Present the compact summary to the user for confirmation
