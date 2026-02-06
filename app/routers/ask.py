from fastapi import APIRouter, Request
from pydantic import BaseModel
from app.services.rag import answer_from_sops


from app.services.sop_ingest import ingest_expenses_sop, search_sops
from app.utils.logging import audit_log

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    top_k: int = 4

@router.post("/sop/ingest")
def sop_ingest(request: Request):
    request_id = request.state.request_id
    result = ingest_expenses_sop()
    audit_log(request_id, "sop_ingested", payload=result)
    return result

@router.post("/sop/search")
def sop_search(body: SearchRequest, request: Request):
    request_id = request.state.request_id
    result = search_sops(query=body.query, top_k=body.top_k)
    audit_log(request_id, "sop_search", payload={"query": body.query, "top_k": body.top_k})
    return result

@router.get("/debug/env")
def debug_env(request: Request):
    import os
    return {
        "has_openai_key": bool(os.getenv("OPENAI_API_KEY", "").strip()),
        "has_todoist_token": bool(os.getenv("TODOIST_API_TOKEN", "").strip()),
        "cwd": os.getcwd(),
        "sop_exists": __import__("pathlib").Path("data/sops/expenses_sop.txt").exists(),
    }

class AskRequest(BaseModel):
    question: str
    top_k: int = 4

@router.post("/ask")
def ask(body: AskRequest, request: Request):
    request_id = request.state.request_id
    result = answer_from_sops(question=body.question, top_k=body.top_k)

    audit_log(request_id, "rag_answer", payload={"question": body.question, "confidence": result.get("confidence")})
    return result


