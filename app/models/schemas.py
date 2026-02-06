from pydantic import BaseModel
from typing import Optional, List

class IntakeRequest(BaseModel):
    channel: str = "whatsapp_mock"
    message: str

class TaskPayload(BaseModel):
    title: str
    description: str
    category: str
    priority: str = "high"
    needs_approval: bool = False
    needs_escalation: bool = False
    sop_confidence: float = 0.0
    sop_citations: List[dict] = []
