# ZEA: AI on-call engineer

ZEA detects production incidents, investigates root causes with evidence,
proposes a code fix, and proves the fix works in a sandbox before a human approves.

Full spec: .plans/zea-ai-oncall-engineer-spec.md. Read it before planning any feature.

## Stack
Python + FastAPI, Postgres (pgvector later), Docker Compose, Next.js + TypeScript + Tailwind.

## Rules
- Hand-rolled state machine for the incident workflow. Do NOT use LangGraph.
- The `events` table is append-only and is the source of truth. Never update or delete events.
- Untrusted text (logs, chat messages) must never reach a tool-using LLM call directly.
- Do not add features beyond the one I ask for.

## How to work with me
- I am learning. Before writing code, give a short plan and wait for my OK.
- Make one small change at a time and explain why in plain language.
- Suggest one test for each change.
