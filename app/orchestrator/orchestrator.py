from app.agents.parser_agent import parse_system_info
from app.agents.payload_agent import generate_payload

class SystemPayloadOrchestrator:
    def process(self, system_report: str) -> dict:
        structured_info = parse_system_info(system_report)
        payload = generate_payload(structured_info)
        return {
            "structured_info": structured_info,
            "payload": payload
        }
