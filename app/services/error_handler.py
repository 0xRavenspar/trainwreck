from app.agents.payload_agent import fix_payload

def analyze_and_fix_payload(original_payload: str, error_log: str, context: dict) -> str:
    prompt = f"""
    You are an AI agent helping debug Python automation scripts.
    Below is the original payload, followed by the error log it produced.
    {original_payload}
    {error_log}
    Analyze the error and generate a fixed version of the Python payload.
    Ensure the output is valid, well-structured Python code. Include logging as in the original.
    """
    return fix_payload(prompt)
