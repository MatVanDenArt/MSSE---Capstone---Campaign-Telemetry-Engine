from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types
from app.services.analytics import mcp_tools, tool_functions
import os

router = APIRouter()

SYSTEM_PROMPT = """You are the Wood Group Campaign Telemetry Engine AI Assistant.
Your primary role is to execute priority actions, query telemetry data, and answer analytical questions about the marketing campaigns.

ZERO-MATH POLICY:
You are strictly forbidden from performing any mathematical calculations yourself (e.g., calculating CPA, ROI, Spend, Pipeline). 
You MUST rely entirely on the provided tools to fetch these metrics if asked.

When a user asks you to execute an action (e.g., 'Draft outreach for X', 'Sync Y to CRM', 'Suggest asset rotation'), acknowledge the command, briefly summarize why it's a good idea based on the context provided in their prompt, and state that the action has been successfully queued or executed. Keep responses concise and conversational (2-3 sentences max).

When a user asks you to **Investigate** a pipeline target (e.g., 'Investigate pipeline target: X'), you should:
1. Act as a strategic advisor. Summarize why this target is important based on the context in their prompt (e.g. number of interactions, recent activity). 
2. Recommend an immediate next step (e.g., drafting an email, syncing to CRM).
3. Append a special execute button at the very end of your response using this exact HTML structure, replacing [ACTION NAME] and [ACTION COMMAND] appropriately:
<div class="mt-4"><button hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{"message": "Execute: [ACTION COMMAND]"}' class="w-full py-2 bg-fuchsia-900/20 hover:bg-fuchsia-600/20 border border-fuchsia-500/50 hover:border-fuchsia-500 text-fuchsia-400 text-[10px] font-bold transition uppercase tracking-widest flex items-center justify-center gap-2"><i class="fa-solid fa-bolt"></i> [ACTION NAME]</button></div>
"""

chat_history = []

@router.post("/chat", response_class=HTMLResponse)
async def handle_chat(message: str = Form(...)):
    global chat_history
    
    user_html = f"""
    <div class="flex gap-3 my-4">
        <div class="w-6 h-6 bg-slate-700 flex items-center justify-center shrink-0 border border-slate-600">
            <i class="fa-solid fa-user text-[10px] text-slate-300"></i>
        </div>
        <div class="text-slate-400 w-full">
            <p class="text-sm font-mono">> {message}</p>
        </div>
    </div>
    """
    
    chat_history.append({"role": "user", "parts": [types.Part.from_text(text=message)]})
    
    try:
        from app.services.llm_rotator import get_genai_client
        
        response = None
        last_err = None
        for _ in range(3):
            try:
                local_client = get_genai_client()
                response = local_client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=chat_history,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_PROMPT,
                        tools=[types.Tool(function_declarations=mcp_tools)],
                        temperature=0.2,
                    )
                )
                break
            except Exception as e:
                last_err = e
        
        if not response:
            raise last_err
        
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
            
            from app.services.llm_rotator import get_genai_client
            
            final_response = None
            last_err = None
            for _ in range(3):
                try:
                    local_client = get_genai_client()
                    final_response = local_client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=chat_history,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            temperature=0.2,
                        )
                    )
                    break
                except Exception as e:
                    last_err = e
                    
            if not final_response:
                raise last_err
            
            text_response = final_response.text
            chat_history.append({"role": "model", "parts": [types.Part.from_text(text=text_response)]})
            
        else:
            text_response = response.text
            chat_history.append({"role": "model", "parts": [types.Part.from_text(text=text_response)]})
            
        ai_html = f"""
        <div class="flex gap-3 my-4">
            <div class="w-6 h-6 bg-fuchsia-600 flex items-center justify-center shrink-0">
                <i class="fa-solid fa-robot text-[10px] text-black"></i>
            </div>
            <div class="w-full">
                <div class="bg-black border border-dark-700 p-4">
                    <div class="text-slate-200 text-sm leading-relaxed">{text_response}</div>
                </div>
            </div>
        </div>
        """
        return user_html + ai_html
        
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            friendly_error = "API Rate Limit Exceeded. You have made too many requests to the AI in a short period. Please wait a moment before trying again."
        else:
            friendly_error = f"Error processing request: {error_msg}"
            
        error_html = f"""
        <div class="flex gap-3 my-4">
            <div class="w-6 h-6 bg-rose-600 flex items-center justify-center shrink-0">
                <i class="fa-solid fa-triangle-exclamation text-[10px] text-black"></i>
            </div>
            <div class="w-full">
                <div class="bg-black border border-rose-900 p-4">
                    <p class="text-rose-400 text-sm font-mono">{friendly_error}</p>
                </div>
            </div>
        </div>
        """
        return user_html + error_html
