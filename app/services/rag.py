from typing import Dict, Any, List
import os
from openai import OpenAI

from app.services.sop_ingest import search_sops

def _oai() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY missing")
    return OpenAI(api_key=key)

def _compute_confidence(matches: List[Dict[str, Any]]) -> float:
    """
    FAISS score here is cosine similarity (inner product on normalized vectors).
    Typical range ~0.2–0.9 depending on content.
    """
    if not matches:
        return 0.0
    top = matches[0].get("score", 0.0)
    # Clamp to [0,1]
    if top < 0:
        return 0.0
    if top > 1:
        return 1.0
    return float(top)

def answer_from_sops(question: str, top_k: int = 4, min_confidence: float = 0.45) -> Dict[str, Any]:
    retrieval = search_sops(query=question, top_k=top_k)
    matches = retrieval["matches"]
    confidence = _compute_confidence(matches)

    citations = [{"source": m["source"], "chunk": m["chunk"], "score": m["score"]} for m in matches]

    # If retrieval is weak, do NOT guess — escalate
    if confidence < min_confidence or len(matches) == 0:
        return {
            "answer": "I don’t have enough information in the approved SOPs to answer confidently. Please escalate to the Chief of Staff.",
            "citations": citations,
            "confidence": confidence,
            "needs_escalation": True,
        }

    context_blocks = []
    for m in matches:
        context_blocks.append(f"[{m['source']} | chunk {m['chunk']} | score {m['score']:.3f}]\n{m['text']}\n")

    system = (
        "You are an internal policy assistant for a family office. "
        "You MUST answer ONLY using the provided SOP excerpts. "
        "If the SOP does not contain the answer, say you don’t know and request escalation. "
        "Keep answers short, operational, and compliance-focused."
    )

    user = (
        f"Question: {question}\n\n"
        "Approved SOP excerpts:\n"
        + "\n".join(context_blocks)
        + "\n\nReturn JSON with keys: answer, next_steps (array), risk_flags (array), used_chunks (array of {source, chunk})."
    )

    client = _oai()
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.1,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
    )

    content = resp.choices[0].message.content

    # Return the model JSON + our meta controls
    return {
        "result": content,  # JSON string (kept as-is for simplicity)
        "citations": citations,
        "confidence": confidence,
        "needs_escalation": False,
    }
