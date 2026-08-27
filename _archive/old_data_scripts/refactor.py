import sys

def main():
    with open("app/api/chat.py", "r", encoding="utf-8") as f:
        content = f.read()
        
    parts = content.split("    try:\n        from app.services.llm_rotator")
    if len(parts) != 2:
        print("Could not find split point")
        return
        
    top_part = parts[0]
    bottom_part = "        from app.services.llm_rotator" + parts[1]
    
    # We need to add active_chat_tasks to the top
    top_part = top_part.replace("chat_history = []\n\n@router.post", "chat_history = []\nactive_chat_tasks = {}\n\n@router.post")
    
    # The new POST return logic:
    new_post_logic = """    import uuid
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
    <div id="agent-stream-{task_id}" hx-ext="sse" sse-connect="/api/chat/stream/{task_id}" sse-swap="message" hx-swap="outerHTML">
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
            clean_html = html.replace('\\n', ' ')
            return f"data: {clean_html}\\n\\n"
            
        message = task_data["message"]
        timeframe = task_data["timeframe"]
        time_context = task_data["time_context"]
        trigger_id = task_data["trigger_id"]
        intent = task_data["intent"]
        reset_context = task_data["reset_context"]
        
        try:
"""
    indented_bottom = []
    for line in bottom_part.split('\n'):
        indented_bottom.append("    " + line)
        
    new_bottom = '\n'.join(indented_bottom)
    
    # We need to inject the yield statements into new_bottom!
    new_bottom = new_bottom.replace(
        "executed_tools.append(func_name)",
        """executed_tools.append(func_name)
                                yield yield_html(f'''
                                <div id="agent-stream-{task_id}">
                                    <div class="flex gap-3 my-4">
                                        <div class="w-6 h-6 bg-fuchsia-600 flex items-center justify-center shrink-0 animate-pulse shadow-[0_0_10px_rgba(192,38,211,0.5)]">
                                            <i class="fa-solid fa-robot text-[10px] text-black"></i>
                                        </div>
                                        <div class="w-full min-w-0 flex items-center text-xs font-mono text-fuchsia-400/80 mt-1">
                                            <i class="fa-solid fa-circle-notch fa-spin mr-2"></i> Executing {func_name}()...
                                        </div>
                                    </div>
                                </div>
                                ''')"""
    )
    
    # Fix returns
    new_bottom = new_bottom.replace(
        "return HTMLResponse(content=f'<div id=\"chat-history\" class=\"flex-1 p-4 overflow-y-auto text-sm space-y-6 custom-scrollbar\" hx-swap-oob=\"innerHTML\">{full_response}</div>')",
        "yield yield_html(f'<div id=\"agent-stream-{task_id}\" hx-swap-oob=\"outerHTML\">{ai_html}</div>')"
    )
    new_bottom = new_bottom.replace(
        "return HTMLResponse(content=full_response)",
        "yield yield_html(f'<div id=\"agent-stream-{task_id}\" hx-swap-oob=\"outerHTML\">{ai_html}</div>')"
    )
    new_bottom = new_bottom.replace(
        "full_response = user_html + ai_html",
        ""
    )
    
    # Error block
    new_bottom = new_bottom.replace(
        "return HTMLResponse(content=f'<div id=\"chat-history\" class=\"flex-1 p-4 overflow-y-auto text-sm space-y-6 custom-scrollbar\" hx-swap-oob=\"innerHTML\">{full_response}</div>')",
        "yield yield_html(f'<div id=\"agent-stream-{task_id}\" hx-swap-oob=\"outerHTML\">{error_html}</div>')"
    )
    new_bottom = new_bottom.replace(
        "return HTMLResponse(content=full_response)",
        "yield yield_html(f'<div id=\"agent-stream-{task_id}\" hx-swap-oob=\"outerHTML\">{error_html}</div>')"
    )
    new_bottom = new_bottom.replace(
        "full_response = user_html + error_html",
        ""
    )
    
    # There are residual if statements checking reset_context.lower() == "true": 
    # Let's just strip them because yielding the HTML twice is annoying.
    new_bottom = new_bottom.replace("        if reset_context.lower() == \"true\":\n            yield yield_html(f'<div id=\"agent-stream-{task_id}\" hx-swap-oob=\"outerHTML\">{ai_html}</div>')\n        yield yield_html(f'<div id=\"agent-stream-{task_id}\" hx-swap-oob=\"outerHTML\">{ai_html}</div>')", 
                                    "        yield yield_html(f'<div id=\"agent-stream-{task_id}\" hx-swap-oob=\"outerHTML\">{ai_html}</div>')")
                                    
    new_bottom = new_bottom.replace("        if reset_context.lower() == \"true\":\n            yield yield_html(f'<div id=\"agent-stream-{task_id}\" hx-swap-oob=\"outerHTML\">{error_html}</div>')\n        yield yield_html(f'<div id=\"agent-stream-{task_id}\" hx-swap-oob=\"outerHTML\">{error_html}</div>')", 
                                    "        yield yield_html(f'<div id=\"agent-stream-{task_id}\" hx-swap-oob=\"outerHTML\">{error_html}</div>')")

    final_content = top_part + new_post_logic + new_bottom + "\n    return StreamingResponse(event_generator(), media_type='text/event-stream')\n"
    
    with open("app/api/chat.py", "w", encoding="utf-8") as f:
        f.write(final_content)
        
    print("Refactoring complete.")

if __name__ == "__main__":
    main()
