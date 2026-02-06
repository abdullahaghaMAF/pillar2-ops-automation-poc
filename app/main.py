from fastapi import FastAPI, Request
from dotenv import load_dotenv
from app.routers import intake
from app.routers import ask


from app.utils.logging import new_request_id, audit_log

load_dotenv()

app = FastAPI(title="Pillar 2 Ops Automation PoC")
app.include_router(intake.router)
app.include_router(ask.router)


@app.middleware("http")
async def add_request_id_and_audit(request: Request, call_next):
    request_id = new_request_id()
    request.state.request_id = request_id

    audit_log(
        request_id=request_id,
        event="http_request",
        payload={"method": request.method, "path": request.url.path},
    )

    try:
        response = await call_next(request)
        audit_log(
            request_id=request_id,
            event="http_response",
            payload={"status_code": response.status_code, "path": request.url.path},
        )
        response.headers["X-Request-Id"] = request_id
        return response
    except Exception as e:
        audit_log(
            request_id=request_id,
            event="http_exception",
            status="error",
            payload={"path": request.url.path},
            error=str(e),
        )
        raise

@app.get("/health")
def health():
    return {"status": "ok"}
