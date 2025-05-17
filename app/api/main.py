from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.orchestrator.orchestrator import SystemPayloadOrchestrator

app = FastAPI()
orchestrator = SystemPayloadOrchestrator()

class SystemReportRequest(BaseModel):
    report: str

@app.post("/generate-payload")
def generate_payload_endpoint(payload: SystemReportRequest):
    try:
        return orchestrator.process(payload.report)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
