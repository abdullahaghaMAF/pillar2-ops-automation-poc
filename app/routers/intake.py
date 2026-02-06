import os
from fastapi import APIRouter, Request

from app.models.schemas import IntakeRequest, TaskPayload
from app.services.router import classify, make_title
from app.services.todoist import get_project_id_by_name, create_task, add_comment
from app.services.rag import answer_from_sops
from app.utils.logging import audit_log

router = APIRouter()

def _build_sop_checklist() -> str:
    # Static checklist extracted from SOP (deterministic, reliable)
    return (
        "SOP Checklist (Expenses):\n"
        "- Payment: ONLY use the SFO card (no personal cards)\n"
        "- Buyer name: QUANT LAB SFO FZCO\n"
        "- TRN: 105069744800001\n"
        "- Billing address: DMCC Business Centre, UT-11-CO-190, Uptown Tower, JLT, Dubai, UAE\n"
        "- Shipping address: Villa 47A, Frond N, Palm Jumeirah, Dubai, UAE\n"
        "- Valid tax invoice required (seller + buyer + TRN + date + amount)\n"
        "- Upload invoice to: SFO Purchases – Invoices (Google Drive)\n"
        "- No mixing personal and company items\n"
    )

@router.post("/intake")
def intake(body: IntakeRequest, request: Request):
    request_id = request.state.request_id

    category, needs_approval = classify(body.message)

    title = make_title(body.message)
    description = f"Channel: {body.channel}\nRaw request: {body.message}"

    # RAG enrichment only for expense/purchase category
    sop_confidence = 0.0
    sop_citations = []
    rag_summary = None
    needs_escalation = False

    if category == "expense_purchase":
        rag = answer_from_sops(question=body.message, top_k=4)
        sop_confidence = rag.get("confidence", 0.0)
        sop_citations = rag.get("citations", [])
        needs_escalation = rag.get("needs_escalation", False)
        rag_summary = rag.get("result") or rag.get("answer")

    payload = TaskPayload(
        title=title,
        description=description,
        category=category,
        priority="high",
        needs_approval=needs_approval,
        needs_escalation=needs_escalation,
        sop_confidence=sop_confidence,
        sop_citations=sop_citations,
    )

    # Create Todoist task
    project_name = os.getenv("TODOIST_PROJECT_NAME", "Inbox")
    project_id = get_project_id_by_name(project_name)

    task = create_task(content=payload.title, description=payload.description, project_id=project_id)

    # Build comment (enrichment)
    comment_parts = [
        "Auto-enrichment (Pillar 2 PoC):",
        f"- Category: {payload.category}",
        f"- Priority: {payload.priority}",
        f"- Needs approval: {payload.needs_approval}",
        f"- SOP confidence: {payload.sop_confidence:.2f}",
    ]

    if payload.category == "expense_purchase":
        comment_parts.append("")
        comment_parts.append(_build_sop_checklist())
        comment_parts.append("RAG Guidance (JSON):")
        comment_parts.append(str(rag_summary))
        comment_parts.append("")
        comment_parts.append("Citations:")
        for c in payload.sop_citations[:4]:
            comment_parts.append(f"- {c.get('source')} | chunk {c.get('chunk')} | score {c.get('score'):.3f}")

        if payload.needs_escalation:
            comment_parts.append("")
            comment_parts.append("⚠️ Escalation Required: SOP signal is low or SOP does not cover this request confidently.")

    comment_text = "\n".join(comment_parts)
    comment = add_comment(task_id=task["id"], content=comment_text)

    audit_log(
        request_id,
        "intake_created_task",
        payload={
            "category": payload.category,
            "needs_approval": payload.needs_approval,
            "needs_escalation": payload.needs_escalation,
            "task_id": task.get("id"),
            "comment_id": comment.get("id"),
        },
    )

    return {"ok": True, "task_id": task.get("id"), "comment_id": comment.get("id"), "payload": payload.model_dump()}
