from pathlib import Path
from typing import List, Dict, Any, Tuple
import os
import json

import numpy as np
import faiss
import tiktoken
from openai import OpenAI

SOP_PATH = Path("data/sops/expenses_sop.txt")

# We’ll store the FAISS index + metadata locally (simple + demo-friendly)
VSTORE_DIR = Path("data/vector_store")
INDEX_FILE = VSTORE_DIR / "sops.index"
META_FILE = VSTORE_DIR / "sops.meta.json"

def _get_openai_client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY is missing in environment/.env")
    return OpenAI(api_key=key)

def _chunk_text(text: str, max_tokens: int = 350, overlap_tokens: int = 50) -> List[str]:
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []
    i = 0
    while i < len(tokens):
        window = tokens[i:i + max_tokens]
        chunks.append(enc.decode(window))
        i += max_tokens - overlap_tokens
    return chunks

def _embed_texts(texts: List[str]) -> np.ndarray:
    import time
    oai = _get_openai_client()
    embeddings: List[List[float]] = []

    batch_size = 16  # smaller batches reduce rate-limit risk
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]

        # retry with exponential backoff on 429
        for attempt in range(5):
            try:
                resp = oai.embeddings.create(
                    model="text-embedding-3-small",
                    input=batch
                )
                embeddings.extend([d.embedding for d in resp.data])
                break
            except Exception as e:
                msg = str(e)
                if "429" in msg or "rate" in msg.lower():
                    sleep_s = 2 ** attempt
                    time.sleep(sleep_s)
                    continue
                raise  # non-429 errors should fail fast

    arr = np.array(embeddings, dtype="float32")
    faiss.normalize_L2(arr)
    return arr


def ingest_expenses_sop() -> Dict[str, Any]:
    if not SOP_PATH.exists():
        raise RuntimeError(f"SOP file not found at: {SOP_PATH}")

    text = SOP_PATH.read_text(encoding="utf-8").strip()
    chunks = _chunk_text(text)

    embeddings = _embed_texts(chunks)
    dim = embeddings.shape[1]

    # Build FAISS index (cosine via inner product on normalized vectors)
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # Save index + metadata
    VSTORE_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_FILE))

    meta = []
    for i, chunk in enumerate(chunks):
        meta.append({
            "id": f"expenses_sop_{i}",
            "source": "SFO EXPENSES SOP",
            "chunk": i,
            "text": chunk
        })

    META_FILE.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"chunks": len(chunks), "store": "faiss", "index_file": str(INDEX_FILE), "meta_file": str(META_FILE)}

def _load_index_and_meta() -> Tuple[faiss.Index, List[Dict[str, Any]]]:
    if not INDEX_FILE.exists() or not META_FILE.exists():
        raise RuntimeError("Vector store not found. Run /sop/ingest first.")

    index = faiss.read_index(str(INDEX_FILE))
    meta = json.loads(META_FILE.read_text(encoding="utf-8"))
    return index, meta

def search_sops(query: str, top_k: int = 4) -> Dict[str, Any]:
    index, meta = _load_index_and_meta()

    q_emb = _embed_texts([query])  # shape (1, dim)
    scores, idxs = index.search(q_emb, top_k)

    matches = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx == -1:
            continue
        item = meta[idx]
        matches.append({
            "source": item["source"],
            "chunk": item["chunk"],
            "score": float(score),  # higher is more similar
            "text": item["text"]
        })

    return {"query": query, "top_k": top_k, "matches": matches}
