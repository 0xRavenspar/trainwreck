import json
from typing import Dict, Any
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config.settings import GOOGLE_API_KEY

system_parser_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", temperature=0.2, google_api_key=GOOGLE_API_KEY
)

SYSTEM_PARSER_PROMPT = PromptTemplate.from_template(
    """You are a specialized System Information Parser agent. 
    Your task is to analyze system reports and extract structured information.
    Format your response as a proper JSON object with detailed information.
    
    System Report to analyze:
    {system_report}
    
    Think through this step by step:
    1. Identify all system components mentioned
    2. Categorize them appropriately
    3. Structure the data in a clean JSON format
    4. Include details like versions, configurations, and specifications
    
    Return only the structured JSON data without additional text.
    """
)


def parse_system_info(system_report: str) -> Dict[str, Any]:
    try:
        response = system_parser_llm.invoke(
            SYSTEM_PARSER_PROMPT.format(system_report=system_report)
        )
        parsed_text = response.content
        start_idx, end_idx = parsed_text.find('{'), parsed_text.rfind('}')
        json_str = parsed_text[start_idx:end_idx+1] if start_idx >= 0 else parsed_text
        return json.loads(json_str)
    except Exception as e:
        return {"error": f"Failed to parse: {str(e)}"}
