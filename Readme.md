# Pillar 2 – Ops / Household Automation Platform (PoC)

This repo is a one-day paid trial PoC for a Family Office “Pillar 2” initiative:
**reduce ad hoc operational requests and repeated mistakes** by introducing:
- a structured intake layer
- routing + task creation in Todoist
- SOP-backed internal AI assistant (RAG)
- conservative escalation (no guessing)
- audit-ready logging

## What this PoC Demonstrates
✅ Intake parsing (chat-style request → structured task)  
✅ Basic routing (expense/purchase vs general)  
✅ Todoist integration: create task + add enrichment comment  
✅ SOP ingestion + semantic search (FAISS)  
✅ Controlled AI assistant:
- answers only from approved SOP excerpts
- citations + confidence score
- escalates if SOP signal is weak  
✅ Logging to `audit.jsonl` with request IDs

## Architecture (High Level)
- **Intake**: WhatsApp/email simulated by `POST /intake`
- **Router**: deterministic categorization for reliability
- **Task System**: Todoist REST API
- **Knowledge**: SOP → chunk → embeddings → FAISS index → retrieval
- **AI Assistant**: SOP-only answers + confidence threshold + escalation
- **Observability**: `audit.jsonl` + request IDs in response headers

(See `docs/architecture.png`)

## Setup
### 1) Create a virtual environment
Windows (PowerShell):
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
