from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types
from app.services.analytics import mcp_tools, tool_functions
import os

router = APIRouter()

try:
    client = genai.Client()
except Exception as e:
    client = None
    print(f"Failed to initialize Gemini Client: {e}")

SYSTEM_PROMPT = """You are the Wood Group Campaign Telemetry Engine AI Assistant.
Your primary role is to provide executive summaries and answer analytical questions about the marketing campaigns.

ZERO-MATH POLICY:
You are strictly forbidden from performing any mathematical calculations yourself (e.g., calculating CPA, ROI, Spend, Pipeline). 
You MUST rely entirely on the provided tools to fetch these metrics.

If a tool fails, politely apologize and state that the metric is currently unavailable.
Keep responses concise, executive, and limited to 3 sentences maximum. Highlight the highest performing persona and biggest drop-off point if applicable.
"""

chat_history = []

@router.post("/chat", response_class=HTMLResponse)
async def handle_chat(message: str = Form(...)):
    global chat_history
    
    if not client:
        return "<div class='text-red-500'>Error: Gemini API Client not initialized. Please ensure GEMINI_API_KEY is set.</div>"
    
    user_html = f"<div class='p-3 bg-blue-100 rounded my-2 text-right'><strong>You:</strong> {message}</div>"
    
    chat_history.append({"role": "user", "parts": [types.Part.from_text(text=message)]})
    
    try:
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=chat_history,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=[types.Tool(function_declarations=mcp_tools)],
                temperature=0.2,
            )
        )
        
        # Unified Tool Calling Loop
        if response.function_calls:
            tool_responses = []
            for function_call in response.function_calls:
                func_name = function_call.name
                args = {k: v for k, v in function_call.args.items()}
                
                if func_name in tool_functions:
                    try:
                        result = tool_functions[func_name](**args)
                    except Exception as e:
                        # Graceful Degradation
                        result = {"error": "tool failed"}
                else:
                    result = {"error": f"Unknown tool: {func_name}"}
                
                tool_responses.append(
                    types.Part.from_function_response(
                        name=func_name,
                        response=result
                    )
                )
            
            chat_history.append(response.candidates[0].content)
            chat_history.append({"role": "user", "parts": tool_responses})
            
            final_response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=chat_history,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.2,
                )
            )
            
            text_response = final_response.text
            chat_history.append({"role": "model", "parts": [types.Part.from_text(text=text_response)]})
            
        else:
            text_response = response.text
            chat_history.append({"role": "model", "parts": [types.Part.from_text(text=text_response)]})
            
        ai_html = f"<div class='p-3 bg-gray-100 rounded my-2'><strong>AI:</strong> {text_response}</div>"
        return user_html + ai_html
        
    except Exception as e:
        return user_html + f"<div class='text-red-500'>Error processing request: {str(e)}</div>"
