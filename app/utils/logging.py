import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

AUDIT_FILE = Path("audit.jsonl")

def new_request_id() -> str:
    return str(uuid.uuid4())

def audit_log(
    request_id: str,
    event: str,
    payload: Optional[Dict[str, Any]] = None,
    status: str = "ok",
    error: Optional[str] = None,
) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "event": event,
        "status": status,
        "payload": payload or {},
        "error": error,
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
