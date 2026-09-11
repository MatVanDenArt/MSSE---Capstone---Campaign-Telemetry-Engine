from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types
from app.services.llm_rotator import mcp_tools, tool_functions
import os
import json
import uuid

router = APIRouter()

SYSTEM_PROMPT = """You are the Wood Group Campaign Telemetry Engine AI Assistant.
Your primary role is to execute priority actions, query telemetry data, and answer analytical questions about the marketing campaigns.

ZERO-MATH POLICY:
You are strictly forbidden from performing any mathematical calculations yourself (e.g., calculating CPA, ROI, Spend, Pipeline). 
You MUST rely entirely on the provided tools to fetch these metrics if asked.

SEQUENTIAL EXECUTION POLICY:
When asked to perform a simulation or projection (e.g., simulate_budget_shift), do NOT guess the budget amounts. 
You MUST FIRST execute a data-gathering tool (e.g., get_budget_pacing) to find your constraints, WAIT for the response, and ONLY THEN execute the simulation tool in a subsequent turn. Do NOT execute them in parallel.

When a user asks you to AUTOMATE or EXECUTE an action (e.g., 'Draft outreach for X', 'Sync Y to CRM', 'Suggest asset rotation'), acknowledge the command, briefly summarize why it's a good idea, and state that it has been successfully queued or executed. Keep responses concise and conversational.
IMPORTANT: A request to 'Review Priority Action' is NOT an execution request. It is a request for analysis.

When a user asks you to **Investigate** a pipeline target (e.g., 'Investigate pipeline target: X'), you should:
1. Act as a strategic advisor. Summarize why this target is important based on the context in their prompt (e.g. number of interactions, recent activity). 
2. Recommend an immediate next step (e.g., drafting an email, syncing to CRM).
3. Append a special execute button at the very end of your response using this exact HTML structure, replacing [ACTION NAME] and [ACTION COMMAND] appropriately:
<div class="mt-4"><button hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{"message": "[ACTION COMMAND]"}' class="w-full py-2 bg-fuchsia-900/20 hover:bg-fuchsia-600/20 border border-fuchsia-500/50 hover:border-fuchsia-500 text-fuchsia-400 text-[10px] font-bold transition uppercase tracking-widest flex items-center justify-center gap-2"><i class="fa-solid fa-bolt"></i> [ACTION NAME]</button></div>

When you retrieve a user's interaction history (using get_user_journey), the tool will return a JSON object with a placeholder indicating the timeline is rendered to the UI. Do NOT attempt to output the timeline yourself. Provide a concise strategic summary of their journey instead.

When you generate A/B test variations (using generate_ab_test_variants), format the response clearly using markdown blockquotes for the copy and bold text for the Control/Variant A/Variant B labels. Include the strategic rationale.
When you draft an outreach sequence (using draft_outreach_sequence), present the sequence clearly using markdown numbered lists or bold headers for each day/step, and italicize the actual email copy. Include the strategic note.
"""

# ---------------------------------------------------------------------------
# Session-scoped state storage
#
# History and pending tasks are stored per session rather than as shared
# module-level globals.  Redis is used when available (Render deployment);
# the local .cache/chat_sessions/ directory is the fallback for development.
#
# Session ID: a plain UUID stored in the "cte_session" cookie.  No signing
# is required for a single-user capstone demo; a production system would use
# itsdangerous.URLSafeTimedSerializer or FastAPI's SessionMiddleware.
# ---------------------------------------------------------------------------

# Re-use the Redis client initialised by llm_rotator so we don't open a
# second connection to the same instance.
from app.services.llm_rotator import redis_client  # may be None

_SESSIONS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", ".cache", "chat_sessions"
)
_SESSION_TTL = 86400  # 24 hours — same as LLM response cache


def _session_file(session_id: str) -> str:
    os.makedirs(_SESSIONS_DIR, exist_ok=True)
    return os.path.join(_SESSIONS_DIR, f"{session_id}.json")


# ── history helpers ─────────────────────────────────────────────────────────

def get_session_history(session_id: str) -> list:
    """Load the chat history for *session_id* from Redis or local JSON."""
    if redis_client:
        try:
            raw = redis_client.get(f"chat:history:{session_id}")
            if raw:
                return json.loads(raw)
        except Exception:
            pass  # fall through to local store

    path = _session_file(session_id)
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
                return data.get("history", [])
        except Exception:
            pass
    return []


def save_session_history(session_id: str, history: list) -> None:
    """Persist *history* for *session_id* to Redis (primary) or local JSON (fallback)."""
    serialised = json.dumps(history, default=_serialise_part)

    if redis_client:
        try:
            redis_client.setex(f"chat:history:{session_id}", _SESSION_TTL, serialised)
            return
        except Exception:
            pass  # fall through to local store

    path = _session_file(session_id)
    try:
        # Merge with existing file so we don't clobber pending tasks
        existing: dict = {}
        if os.path.exists(path):
            with open(path, "r") as f:
                existing = json.load(f)
        existing["history"] = history
        with open(path, "w") as f:
            json.dump(existing, f, default=_serialise_part)
    except Exception:
        pass


# ── task helpers ─────────────────────────────────────────────────────────────

def save_task(task_id: str, task_data: dict) -> None:
    """Store a pending SSE task by *task_id*."""
    serialised = json.dumps(task_data)

    if redis_client:
        try:
            # Tasks only need to live long enough for the SSE stream to open
            redis_client.setex(f"chat:task:{task_id}", 300, serialised)
            return
        except Exception:
            pass

    path = _session_file(task_data.get("session_id", "unknown"))
    try:
        existing: dict = {}
        if os.path.exists(path):
            with open(path, "r") as f:
                existing = json.load(f)
        tasks = existing.get("tasks", {})
        tasks[task_id] = task_data
        existing["tasks"] = tasks
        with open(path, "w") as f:
            json.dump(existing, f)
    except Exception:
        pass


def pop_task(task_id: str) -> dict | None:
    """Retrieve and delete a pending task by *task_id*."""
    if redis_client:
        try:
            raw = redis_client.getdel(f"chat:task:{task_id}")
            if raw:
                return json.loads(raw)
        except Exception:
            pass

    # Scan local session files for the task (fallback)
    try:
        if os.path.exists(_SESSIONS_DIR):
            for fname in os.listdir(_SESSIONS_DIR):
                fpath = os.path.join(_SESSIONS_DIR, fname)
                try:
                    with open(fpath, "r") as f:
                        data = json.load(f)
                    tasks = data.get("tasks", {})
                    if task_id in tasks:
                        task = tasks.pop(task_id)
                        with open(fpath, "w") as f:
                            json.dump(data, f)
                        return task
                except Exception:
                    continue
    except Exception:
        pass
    return None


# ── serialisation helper ──────────────────────────────────────────────────

def _serialise_part(obj):
    """JSON default encoder: convert google.genai Part objects to plain dicts."""
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


# ── session cookie helper ─────────────────────────────────────────────────

_COOKIE_NAME = "cte_session"


def get_or_create_session_id(request: Request) -> tuple[str, bool]:
    """Return (session_id, is_new).  is_new=True means the caller must set the cookie."""
    sid = request.cookies.get(_COOKIE_NAME)
    if sid:
        return sid, False
    return uuid.uuid4().hex, True


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/chat", response_class=HTMLResponse)
def handle_chat(
    request: Request,
    message: str = Form(...),
    timeframe: int = Form(0),
    time_context: str = Form(None),
    trigger_id: str = Form(None),
    intent: str = Form(None),
    reset_context: str = Form("false"),
    campaign_id: str = Form(None),
):
    session_id, is_new_session = get_or_create_session_id(request)
    chat_history = get_session_history(session_id)

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
    while len(chat_history) > 12:
        chat_history.pop(0)
        while chat_history:
            first = chat_history[0]
            role = first.get("role") if isinstance(first, dict) else getattr(first, "role", None)
            parts = first.get("parts") if isinstance(first, dict) else getattr(first, "parts", [])

            is_func_resp = False
            if parts:
                for p in parts:
                    if isinstance(p, dict) and "function_response" in p:
                        is_func_resp = True
                    elif hasattr(p, "function_response") and p.function_response:
                        is_func_resp = True

            if role == "user" and not is_func_resp:
                break
            chat_history.pop(0)

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
            simulated_response += f'<script>window.dispatchEvent(new CustomEvent("task-resolved", {{detail: {{id: "{trigger_id}"}}}}))</script>'

        chat_history.append({"role": "model", "parts": [types.Part.from_text(text="Action Executed Successfully.")]})
        save_session_history(session_id, chat_history)

        full_response = user_html + simulated_response
        response = HTMLResponse(content=full_response)
        if reset_context.lower() == "true":
            response = HTMLResponse(content=f'<div id="chat-history" class="flex-1 p-4 overflow-y-auto text-sm space-y-6 custom-scrollbar" hx-swap-oob="innerHTML">{full_response}</div>')
        if is_new_session:
            response.set_cookie(_COOKIE_NAME, session_id, max_age=_SESSION_TTL, httponly=True, samesite="lax")
        return response

    task_id = uuid.uuid4().hex
    save_task(task_id, {
        "session_id": session_id,
        "message": message,
        "timeframe": timeframe,
        "time_context": time_context,
        "trigger_id": trigger_id,
        "intent": intent,
        "reset_context": reset_context,
        "campaign_id": campaign_id,
        "chat_history": json.dumps(chat_history, default=_serialise_part),
    })

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
        content = f'<div id="chat-history" class="flex-1 p-4 overflow-y-auto text-sm space-y-6 custom-scrollbar" hx-swap-oob="innerHTML">{full_response}</div>'
    else:
        content = full_response

    response = HTMLResponse(content=content)
    if is_new_session:
        response.set_cookie(_COOKIE_NAME, session_id, max_age=_SESSION_TTL, httponly=True, samesite="lax")
    return response


from fastapi.responses import StreamingResponse


@router.get("/chat/stream/{task_id}")
def chat_stream(task_id: str):
    task_data = pop_task(task_id)
    if not task_data:
        return StreamingResponse(iter([]), media_type="text/event-stream")

    def event_generator():
        def yield_html(html):
            clean_html = html.replace('\n', ' ')
            return f"data: {clean_html}\n\n"

        session_id = task_data["session_id"]
        message = task_data["message"]
        timeframe = task_data["timeframe"]
        time_context = task_data["time_context"]
        trigger_id = task_data["trigger_id"]
        intent = task_data["intent"]
        reset_context = task_data["reset_context"]
        campaign_id = task_data.get("campaign_id")

        # Restore history snapshot captured at request time so concurrent
        # sessions don't interfere with each other.
        try:
            chat_history = json.loads(task_data["chat_history"])
        except Exception:
            chat_history = get_session_history(session_id)

        try:
            from app.services.llm_rotator import get_genai_client
            captured_html_timeline = None

            # Inject the UI state into the system prompt
            if time_context:
                context_prompt = SYSTEM_PROMPT + f"\n\nCURRENT UI CONTEXT:\n{time_context}. You MUST scope your analysis to this specific timeframe anomaly and ignore the global timeframe."
            else:
                context_prompt = SYSTEM_PROMPT + f"\n\nCURRENT UI CONTEXT:\nThe user currently has their dashboard timeframe filtered to: {timeframe} days (0 means All Time). If they ask for metrics without specifying a date, use this timeframe."
            if campaign_id:
                context_prompt += f"\nThe user is currently viewing the campaign '{campaign_id}'. You MUST scope all your data and analysis specifically to this campaign by passing it to your tools."

            if intent == "review" and trigger_id:
                context_prompt += f"""\n\nCRITICAL INSTRUCTION FOR THIS PROMPT:
    The user is reviewing a Priority Action from the dashboard Action Center. 
    Act as a strategic advisor. Analyze the action details provided by the user. Explain why it is a priority and what the impact is based on your telemetry tools if needed.
    
    After your analysis, you MUST provide exactly 1 to 3 concrete automated next steps (e.g. "Draft Follow-Up Email", "Sync to Salesforce").
    
    To format this, you MUST place a `### Recommended Action(s)` header immediately before the buttons.
    Then, for EACH suggested action, output an HTML button using this EXACT structure, replacing [ACTION NAME] with a short label (e.g. "Draft Email"), [ACTION COMMAND] with the specific automated instruction you would want the user to click, and [INTENT] with either 'automate' (if pushing data to a CRM/System) or 'chat' (if generating content like drafting an email):
    
    <button onclick="window.dispatchEvent(new CustomEvent('task-resolved', {{detail: {{id: '{trigger_id}'}}}}))\" hx-post="/api/chat" hx-target="#chat-history" hx-swap="beforeend" hx-indicator="#loading-indicator" hx-vals='{{"message": "[ACTION COMMAND]", "intent": "[INTENT]", "trigger_id": "{trigger_id}", "campaign_id": "{campaign_id}", "timeframe": "{timeframe}"}}' class="mb-2 w-full py-1.5 bg-fuchsia-900/40 hover:bg-fuchsia-600/40 border border-fuchsia-500/50 hover:border-fuchsia-400 text-fuchsia-300 hover:text-white text-[10px] font-bold transition-all uppercase tracking-widest flex items-center justify-center gap-2 rounded"><i class="fa-solid fa-bolt"></i> [ACTION NAME]</button>
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
            last_call_signature = None  # Tracks (tool_name, frozen_args) to detect stuck loops
            for _ in range(5):
                if current_response.function_calls:
                    tool_responses = []
                    for function_call in current_response.function_calls:
                        func_name = function_call.name
                        args = {k: v for k, v in function_call.args.items()}

                        # Guard: detect the model calling the same tool with identical args repeatedly
                        call_signature = (func_name, str(sorted(args.items())))
                        if call_signature == last_call_signature:
                            tool_responses.append(
                                types.Part.from_function_response(
                                    name=func_name,
                                    response={
                                        "error": f"Tool '{func_name}' was already called with these exact arguments and failed. "
                                                 f"Do NOT retry with the same inputs. Either use a different tool or "
                                                 f"respond to the user with what you know so far."
                                    }
                                )
                            )
                            continue
                        last_call_signature = call_signature

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

                        if func_name in tool_functions:
                            try:
                                result = tool_functions[func_name](**args)
                                if not isinstance(result, dict):
                                    result = {"data": result}

                                if func_name == "get_user_journey" and "html_timeline" in result:
                                    captured_html_timeline = result["html_timeline"]
                                    result["html_timeline"] = "[HTML TIMELINE RENDERED TO UI - DO NOT OUTPUT HTML. JUST PROVIDE A STRATEGIC SUMMARY]"
                            except Exception as e:
                                # Informative degradation: tell the model what failed and why
                                result = {
                                    "error": f"Tool '{func_name}' raised an exception: {str(e)}. "
                                             f"Arguments provided were: {args}. "
                                             f"Check that all required arguments are present and correctly typed. "
                                             f"Do NOT retry this tool with the same arguments."
                                }
                        else:
                            result = {"error": f"Unknown tool: {func_name}"}

                        tool_responses.append(
                            types.Part.from_function_response(
                                name=func_name,
                                response=result
                            )
                        )

                    chat_history.append({"role": "model", "parts": current_response.candidates[0].content.parts})
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

            # Persist the updated history for this session
            save_session_history(session_id, chat_history)

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

            clear_btn = "<div class='mt-4 border-t border-dark-800 pt-4'><button onclick=\"this.innerHTML='<i class=&quot;fa-solid fa-check-double&quot;></i> Cleared'; this.disabled=true; this.classList.add('opacity-50', 'cursor-not-allowed'); window.dispatchEvent(new CustomEvent('task-resolved', {detail: {id: '" + trigger_id + "'}}));\" class='w-full py-1.5 bg-dark-800 hover:bg-dark-700 border border-dark-600 hover:border-slate-400 text-slate-400 hover:text-white text-[10px] font-bold transition-all uppercase tracking-widest flex items-center justify-center gap-2 rounded'><i class='fa-solid fa-check'></i> Clear Alert from Queue</button></div>" if (intent == "review" and trigger_id) else ""
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
            <div class="flex gap-4">
                <div class="w-8 h-8 rounded-full bg-fuchsia-500/20 border border-fuchsia-500/30 flex items-center justify-center flex-shrink-0 mt-1">
                    <i class="fa-solid fa-robot text-fuchsia-400 text-sm"></i>
                </div>
                <div class="w-full min-w-0">
                    <div class="bg-black border border-dark-700 p-4 w-full">
                        <div class="text-slate-200 text-sm leading-relaxed copilot-markdown break-words overflow-x-hidden">{parsed_html}</div>
                        {clear_btn}
                    </div>
                </div>
            </div>
            """

            yield yield_html(f'<div id="agent-stream-{task_id}" hx-swap-oob="outerHTML">{ai_html}</div>')

        except Exception as e:
            # Roll back the user message that was added to local history
            if chat_history and chat_history[-1].get("role") == "user":
                chat_history.pop()
            save_session_history(session_id, chat_history)

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
