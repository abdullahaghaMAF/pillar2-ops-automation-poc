import os
import requests

TODOIST_API_BASE = "https://api.todoist.com/rest/v2"

def _headers():
    token = os.getenv("TODOIST_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TODOIST_API_TOKEN is missing in environment/.env")
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def get_projects():
    r = requests.get(f"{TODOIST_API_BASE}/projects", headers=_headers(), timeout=20)
    r.raise_for_status()
    return r.json()

def get_project_id_by_name(project_name: str) -> str:
    projects = get_projects()
    for p in projects:
        if p.get("name") == project_name:
            return p["id"]
    raise RuntimeError(f"Todoist project not found: {project_name}")

def create_task(content: str, description: str = "", project_id: str | None = None):
    payload = {"content": content}
    if description:
        payload["description"] = description
    if project_id:
        payload["project_id"] = project_id

    r = requests.post(f"{TODOIST_API_BASE}/tasks", json=payload, headers=_headers(), timeout=20)
    r.raise_for_status()
    return r.json()
def add_comment(task_id: str, content: str):
    payload = {"task_id": task_id, "content": content}
    r = requests.post(f"{TODOIST_API_BASE}/comments", json=payload, headers=_headers(), timeout=20)
    r.raise_for_status()
    return r.json()
