from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.orchestrator.orchestrator import SystemPayloadOrchestrator
from app.services.error_handler import analyze_and_fix_payload
from typing import Optional, Dict


app = FastAPI()
orchestrator = SystemPayloadOrchestrator()

class SystemReportRequest(BaseModel):
    report: str

class ErrorFixRequest(BaseModel):
    payload: str
    error_log: str
    context: Optional[Dict] = {}

@app.post("/generate-payload")
def generate_payload_endpoint(payload: SystemReportRequest):
    try:
        return orchestrator.process(payload.report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/error")
async def handle_error(req: ErrorFixRequest):
    fixed_payload = analyze_and_fix_payload(
        original_payload=req.payload,
        error_log=req.error_log,
        context=req.context
    )
    return {
        "payload": fixed_payload
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        clients.remove(websocket)

@app.post("/webhook")
async def receive_data(data: dict):
    for client in clients:
        await client.send_text(json.dumps(data))
    return {"status": "sent to clients"}