from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types
from app.services.llm_rotator import mcp_tools, tool_functions
import os

router = APIRouter()

SYSTEM_PROMPT = """You are the Wood Group Campaign Telemetry Engine AI Assistant.
Your primary role is to execute priority actions, query telemetry data, and answer analytical questions about the marketing campaigns.

ZERO-MATH POLICY:
You are strictly forbidden from performing any mathematical calculations yourself (e.g., calculating CPA, ROI, Spend, Pipeline). 
You MUST rely entirely on the provided tools to fetch these metrics if asked.

When a user asks you to AUTOMATE or EXECUTE an action (e.g., 'Draft outreach for X', 'Sync Y to CRM', 'Suggest asset rotation'), acknowledge the command, briefly summarize why it's a good idea, and state that it has been successfully queued or executed. Keep responses concise and conversational.
IMPORTANT: A request to 'Review Priority Action' is NOT an execution request. It is a request for analysis.

When a user asks you to **Investigate** a pipeline target (e.g., 'Investigate pipeline target: X'), you should:
1. Act as a strategic advisor. Summarize why this target is important based on the context in their prompt (e.g. number of interactions, recent activity). 
2. Recommend an immediate next step (e.g., drafting an email, syncing to CRM).
3. Append a special execute button at the very end of your response using this exact HTML structure, replacing [ACTION NAME] and [ACTION COMMAND] appropriately:
<div class="mt-4"><button hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{"message": "Execute: [ACTION COMMAND]"}' class="w-full py-2 bg-fuchsia-900/20 hover:bg-fuchsia-600/20 border border-fuchsia-500/50 hover:border-fuchsia-500 text-fuchsia-400 text-[10px] font-bold transition uppercase tracking-widest flex items-center justify-center gap-2"><i class="fa-solid fa-bolt"></i> [ACTION NAME]</button></div>

When you retrieve a user's interaction history (using get_user_journey), the tool will return a JSON object with a placeholder indicating the timeline is rendered to the UI. Do NOT attempt to output the timeline yourself. Provide a concise strategic summary of their journey instead.

When you generate A/B test variations (using generate_ab_test_variants), format the response clearly using markdown blockquotes for the copy and bold text for the Control/Variant A/Variant B labels. Include the strategic rationale.
When you draft an outreach sequence (using draft_outreach_sequence), present the sequence clearly using markdown numbered lists or bold headers for each day/step, and italicize the actual email copy. Include the strategic note.
"""

chat_history = []
active_chat_tasks = {}

@router.post("/chat", response_class=HTMLResponse)
def handle_chat(message: str = Form(...), timeframe: int = Form(0), time_context: str = Form(None), trigger_id: str = Form(None), intent: str = Form(None), reset_context: str = Form("false")):
    global chat_history
    
    context_breakers = [
        "review priority action:",
        "investigate pipeline target:",
        "draft outreach strategy for",
        "generate campaign report",
        "analyze funnel metrics",
        "check asset fatigue",
        "investigate target:",
    ]
    
    msg_lower = message.strip().lower()
    auto_reset = any(msg_lower.startswith(b) for b in context_breakers)
    
    if reset_context.lower() == "true" or auto_reset:
        chat_history = []
    
    # Prevent chat history from growing unbounded and hanging the API
    if len(chat_history) > 12:
        chat_history = chat_history[-12:]
        
    display_message = message
    if ". Suggested Action: " in display_message:
        display_message = display_message.split(". Suggested Action: ")[0]
        
    user_html = f"""
    <div class="flex gap-3 my-4">
        <div class="w-6 h-6 bg-slate-700 flex items-center justify-center shrink-0 border border-slate-600">
            <i class="fa-solid fa-user text-[10px] text-slate-300"></i>
        </div>
        <div class="text-slate-400 w-full">
            <p class="text-sm font-mono">> {display_message}</p>
        </div>
    </div>
    """
    
    import time
    
    chat_history.append({"role": "user", "parts": [types.Part.from_text(text=message)]})
    
    if intent == "automate" or (trigger_id and not intent and not message.lower().startswith("draft")):
        # Artificial execution simulation
        time.sleep(1.5)
        
        logo_icon = "fa-server"
        system_name = "Internal System"
        msg_lower = message.lower()
        status_msg = "Record synchronized successfully"
        
        if "crm" in msg_lower or "opportunity" in msg_lower or "sql" in msg_lower or "salesforce" in msg_lower:
            logo_icon = "fa-salesforce text-sky-400"
            system_name = "Salesforce CRM"
            status_msg = "Lead intent data synchronized successfully"
        elif "campaign" in msg_lower or "linkedin" in msg_lower or "ads" in msg_lower:
            logo_icon = "fa-linkedin text-blue-500"
            system_name = "LinkedIn Ads"
            if "budget" in msg_lower or "shift" in msg_lower:
                status_msg = "Budget reallocation applied successfully"
            else:
                status_msg = "Campaign parameters updated"
        elif "email" in msg_lower or "outreach" in msg_lower or "newsletter" in msg_lower or "marketo" in msg_lower:
            logo_icon = "fa-envelope text-fuchsia-400"
            system_name = "Marketo"
            status_msg = "Outreach workflow triggered successfully"

        icon_class = logo_icon.split(' ')[0]
        icon_color = ' '.join(logo_icon.split(' ')[1:]) if ' ' in logo_icon else 'text-slate-400'
        
        simulated_response = f"""
        <div class="flex gap-3 my-4">
            <div class="w-6 h-6 bg-slate-900 flex items-center justify-center shrink-0 border border-slate-700">
                <i class="fa-brands {icon_class} text-[10px] {icon_color}"></i>
            </div>
            <div class="w-full">
                <div class="bg-black border border-dark-700 rounded p-3 font-mono text-xs shadow-[inset_0_0_10px_rgba(0,0,0,0.5)]">
                    <div class="flex justify-between items-center border-b border-dark-800 pb-2 mb-2">
                        <span class="text-slate-500 uppercase tracking-widest">{system_name}</span>
                        <span class="text-emerald-500 font-bold">200 OK</span>
                    </div>
                    <div class="text-slate-300">
                        <span class="text-slate-500">Action:</span> {message}
                    </div>
                    <div class="text-slate-300 mt-1">
                        <span class="text-slate-500">Status:</span> {status_msg}
                    </div>
                </div>
            </div>
        </div>
        """
        if trigger_id:
            simulated_response += f'<script>window.dispatchEvent(new CustomEvent("task-resolved", {{detail: {{id: "{trigger_id}"}}}}));</script>'
            
        chat_history.append({"role": "model", "parts": [types.Part.from_text(text="Action Executed Successfully.")]})
        
        full_response = user_html + simulated_response
        if reset_context.lower() == "true":
            return HTMLResponse(content=f'<div id="chat-history" class="flex-1 p-4 overflow-y-auto text-sm space-y-6 custom-scrollbar" hx-swap-oob="innerHTML">{full_response}</div>')
        return HTMLResponse(content=full_response)
    
    import uuid
    task_id = uuid.uuid4().hex
    active_chat_tasks[task_id] = {
        "message": message,
        "timeframe": timeframe,
        "time_context": time_context,
        "trigger_id": trigger_id,
        "intent": intent,
        "reset_context": reset_context
    }
    
    sse_html = f'''
    <div id="agent-stream-{task_id}" hx-ext="sse" sse-connect="/api/chat/stream/{task_id}" sse-swap="message" hx-swap="innerHTML">
        <div class="flex gap-3 my-4">
            <div class="w-6 h-6 bg-fuchsia-600 flex items-center justify-center shrink-0 animate-pulse shadow-[0_0_10px_rgba(192,38,211,0.5)]">
                <i class="fa-solid fa-robot text-[10px] text-black"></i>
            </div>
            <div class="w-full min-w-0 flex items-center text-xs font-mono text-fuchsia-400/80 mt-1">
                <i class="fa-solid fa-circle-notch fa-spin mr-2"></i> Initializing Agent Workspace...
            </div>
        </div>
    </div>
    '''
    
    full_response = user_html + sse_html
    if reset_context.lower() == "true":
        return HTMLResponse(content=f'<div id="chat-history" class="flex-1 p-4 overflow-y-auto text-sm space-y-6 custom-scrollbar" hx-swap-oob="innerHTML">{full_response}</div>')
    return HTMLResponse(content=full_response)

from fastapi.responses import StreamingResponse

@router.get("/chat/stream/{task_id}")
def chat_stream(task_id: str):
    task_data = active_chat_tasks.pop(task_id, None)
    if not task_data:
        return StreamingResponse(iter([]), media_type="text/event-stream")
        
    def event_generator():
        def yield_html(html):
            clean_html = html.replace('\n', ' ')
            return f"data: {clean_html}\n\n"
            
        message = task_data["message"]
        timeframe = task_data["timeframe"]
        time_context = task_data["time_context"]
        trigger_id = task_data["trigger_id"]
        intent = task_data["intent"]
        reset_context = task_data["reset_context"]
        
        try:
            from app.services.llm_rotator import get_genai_client
            captured_html_timeline = None
            
            # Inject the UI state into the system prompt
            if time_context:
                context_prompt = SYSTEM_PROMPT + f"\n\nCURRENT UI CONTEXT:\n{time_context}. You MUST scope your analysis to this specific timeframe anomaly and ignore the global timeframe."
            else:
                context_prompt = SYSTEM_PROMPT + f"\n\nCURRENT UI CONTEXT:\nThe user currently has their dashboard timeframe filtered to: {timeframe} days (0 means All Time). If they ask for metrics without specifying a date, use this timeframe."
                
            if intent == "review" and trigger_id:
                context_prompt += f"""\n\nCRITICAL INSTRUCTION FOR THIS PROMPT:
    The user is reviewing a Priority Action from the dashboard Action Center. 
    Act as a strategic advisor. Analyze the action details provided by the user. Explain why it is a priority and what the impact is based on your telemetry tools if needed.
    
    After your analysis, you MUST provide exactly 1 to 3 concrete automated next steps (e.g. "Draft Follow-Up Email", "Sync to Salesforce").
    
    To format this, you MUST place a `### Recommended Action(s)` header immediately before the buttons.
    Then, for EACH suggested action, output an HTML button using this EXACT structure, replacing [ACTION NAME] with a short label (e.g. "Draft Email"), [ACTION COMMAND] with the specific automated instruction you would want the user to click, and [INTENT] with either 'automate' (if pushing data to a CRM/System) or 'chat' (if generating content like drafting an email):
    
    <button onclick="window.dispatchEvent(new CustomEvent('task-resolved', {{detail: {{id: '{trigger_id}'}}}}))" hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{{"message": "[ACTION COMMAND]", "intent": "[INTENT]", "trigger_id": "{trigger_id}"}}' class="mb-2 w-full py-1.5 bg-fuchsia-900/40 hover:bg-fuchsia-600/40 border border-fuchsia-500/50 hover:border-fuchsia-400 text-fuchsia-300 hover:text-white text-[10px] font-bold transition-all uppercase tracking-widest flex items-center justify-center gap-2 rounded"><i class="fa-solid fa-bolt"></i> [ACTION NAME]</button>
    """
            
            response = None
            last_err = None
            from app.services.llm_rotator import get_genai_client, mark_key_exhausted
            
            for _ in range(5):
                try:
                    local_client = get_genai_client()
                    response = local_client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=chat_history,
                        config=types.GenerateContentConfig(
                            system_instruction=context_prompt,
                            tools=[types.Tool(function_declarations=mcp_tools)],
                            temperature=0.2,
                        )
                    )
                    break
                except Exception as e:
                    last_err = e
                    error_msg = str(e)
                    if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                        if hasattr(local_client, 'api_key'):
                            mark_key_exhausted(local_client.api_key)
            
            if not response:
                raise last_err
            
            # Unified Tool Calling Loop
            current_response = response
            executed_tools = []
            for _ in range(5):
                if current_response.function_calls:
                    tool_responses = []
                    for function_call in current_response.function_calls:
                        func_name = function_call.name
                        executed_tools.append(func_name)
                        friendly_name = func_name.replace('_', ' ').title()
                        if func_name == "get_user_journey": friendly_name = "Analyzing User Journey"
                        elif func_name == "get_intent_surge_signals": friendly_name = "Detecting Intent Surge Signals"
                        elif func_name == "map_buying_committee": friendly_name = "Mapping Buying Committee"
                        elif func_name == "get_asset_impact_matrix": friendly_name = "Evaluating Asset Impact"
                        
                        yield yield_html(f'''
                            <div class="flex gap-3 my-4">
                                <div class="w-6 h-6 bg-fuchsia-600 flex items-center justify-center shrink-0 animate-pulse shadow-[0_0_10px_rgba(192,38,211,0.5)]">
                                    <i class="fa-solid fa-robot text-[10px] text-black"></i>
                                </div>
                                <div class="w-full min-w-0 flex items-center text-xs font-mono text-fuchsia-400/80 mt-1">
                                    <i class="fa-solid fa-circle-notch fa-spin mr-2"></i> {friendly_name}...
                                </div>
                            </div>
                        ''')
                        args = {k: v for k, v in function_call.args.items()}
                        
                        if func_name in tool_functions:
                            try:
                                result = tool_functions[func_name](**args)
                                if not isinstance(result, dict):
                                    result = {"data": result}
                                    
                                if func_name == "get_user_journey" and "html_timeline" in result:
                                    captured_html_timeline = result["html_timeline"]
                                    result["html_timeline"] = "[HTML TIMELINE RENDERED TO UI - DO NOT OUTPUT HTML. JUST PROVIDE A STRATEGIC SUMMARY]"
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
                    
                    chat_history.append(current_response.candidates[0].content)
                    chat_history.append({"role": "user", "parts": tool_responses})
                    
                    from app.services.llm_rotator import get_genai_client
                    
                    last_err = None
                    for attempt in range(5):
                        try:
                            local_client = get_genai_client()
                            current_response = local_client.models.generate_content(
                                model='gemini-3.6-flash',
                                contents=chat_history,
                                config=types.GenerateContentConfig(
                                    system_instruction=context_prompt,
                                    tools=[types.Tool(function_declarations=mcp_tools)],
                                    temperature=0.2,
                                )
                            )
                            break
                        except Exception as e:
                            last_err = e
                            error_msg = str(e)
                            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                                if hasattr(local_client, 'api_key'):
                                    mark_key_exhausted(local_client.api_key)
                                    
                            if attempt == 4:
                                raise e
                else:
                    break
                    
            text_response = current_response.text or "I have reviewed the information based on the available data."
            
            if captured_html_timeline:
                timeline_accordion = f"""
<details class="mt-4 border border-dark-600 bg-dark-900 text-slate-300">
    <summary class="p-3 text-xs font-bold uppercase tracking-widest cursor-pointer hover:bg-dark-800 transition">View Interaction History</summary>
    <div class="p-4">
        {captured_html_timeline}
    </div>
</details>
                """
                text_response += "\n" + timeline_accordion
                
            chat_history.append({"role": "model", "parts": [types.Part.from_text(text=text_response)]})
            
            if executed_tools:
                # Create an accordion showing the tools used
                def get_friendly_name(t):
                    mapping = {
                        "get_user_journey": "Analyzed User Journey",
                        "get_intent_surge_signals": "Detected Intent Surge Signals",
                        "map_buying_committee": "Mapped Buying Committee",
                        "get_asset_impact_matrix": "Evaluated Asset Impact",
                        "compare_asset_baselines": "Compared Asset Baselines",
                        "evaluate_trickle_threshold": "Evaluated Traffic Decay",
                        "simulate_budget_shift": "Simulated Budget Shift",
                        "get_executive_pipeline_kpis": "Fetched Executive KPIs"
                    }
                    return mapping.get(t, t.replace('_', ' ').title() + " Completed")
                    
                tools_html = "".join([f"<div>> {get_friendly_name(t)}</div>" for t in executed_tools])
                tool_count = len(executed_tools)
                tool_ui = f"""<div x-data="{{ expanded: false }}" class="mb-4 bg-dark-900/50 rounded-lg p-3 border border-dark-800 w-full shadow-inner">
    <button @click="expanded = !expanded" type="button" class="text-[10px] uppercase font-bold tracking-widest text-slate-400 hover:text-fuchsia-400 transition-colors flex items-center gap-2 w-full focus:outline-none">
    <i class="fa-solid fa-microchip"></i> 
    Executed {tool_count} Autonomous Tool{'s' if tool_count > 1 else ''}
    <i class="fa-solid fa-chevron-down ml-auto transition-transform duration-200" :class="expanded ? 'rotate-180' : ''"></i>
    </button>
    <div x-show="expanded" x-collapse class="mt-3 pt-3 border-t border-dark-800 text-[10px] text-fuchsia-400/80 font-mono space-y-1 overflow-x-auto">
    {tools_html}
    </div>
    </div>
    """
                text_response = tool_ui + "\n" + text_response
                
            import markdown
            parsed_html = markdown.markdown(text_response)
            
            ai_html = f"""
            <style>
            .copilot-markdown p {{ margin-bottom: 1em; }}
            .copilot-markdown h1, .copilot-markdown h2, .copilot-markdown h3, .copilot-markdown h4 {{ font-weight: bold; margin-top: 1.5em; margin-bottom: 0.5em; color: #fdf4ff; }}
            .copilot-markdown ul:not(.list-none) {{ list-style-type: disc; padding-left: 1.5em; margin-bottom: 1em; }}
            .copilot-markdown ol:not(.list-none) {{ list-style-type: decimal; padding-left: 1.5em; margin-bottom: 1em; }}
            .copilot-markdown li {{ margin-bottom: 0.5em; }}
            .copilot-markdown strong {{ font-weight: bold; color: #fdf4ff; }}
            </style>
            <div class="flex gap-3 my-4">
                <div class="w-6 h-6 bg-fuchsia-600 flex items-center justify-center shrink-0">
                    <i class="fa-solid fa-robot text-[10px] text-black"></i>
                </div>
                <div class="w-full min-w-0">
                    <div class="bg-black border border-dark-700 p-4 w-full">
                        <div class="text-slate-200 text-sm leading-relaxed copilot-markdown break-words overflow-x-hidden">{parsed_html}</div>
                        {"<div class='mt-4 border-t border-dark-800 pt-4'><button onclick=\"this.innerHTML='<i class=&quot;fa-solid fa-check-double&quot;></i> Cleared'; this.disabled=true; this.classList.add('opacity-50', 'cursor-not-allowed'); window.dispatchEvent(new CustomEvent('task-resolved', {detail: {id: '" + trigger_id + "'}}));\" class='w-full py-1.5 bg-dark-800 hover:bg-dark-700 border border-dark-600 hover:border-slate-400 text-slate-400 hover:text-white text-[10px] font-bold transition-all uppercase tracking-widest flex items-center justify-center gap-2 rounded'><i class='fa-solid fa-check'></i> Clear Alert from Queue</button></div>" if (intent == "review" and trigger_id) else ""}
                    </div>
                </div>
            </div>
            """
            
            yield yield_html(f'<div id="agent-stream-{task_id}" hx-swap-oob="outerHTML">{ai_html}</div>')
            
        except Exception as e:
            chat_history.pop() # Remove the user's message if there was an error
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
            
            yield yield_html(f'<div id="agent-stream-{task_id}" hx-swap-oob="outerHTML">{error_html}</div>')
    
    return StreamingResponse(event_generator(), media_type='text/event-stream')
