Antigravity Development Runbook (High-Fidelity)
===============================================

This runbook contains the master prompts to initialize and build the Telemetry Engine according to our agreed-upon architecture. Execute these sequentially in Antigravity.

1\. Environment & Base Foundation (Repository & Router Setup)
-------------------------------------------------------------

> **PROMPT:** "Initialize a FastAPI project following a strict Domain-Driven folder structure: /app (main.py, /api, /services, /data, /templates), /tests, and a Dockerfile. Use requirements.txt to include fastapi, uvicorn, pandas, faker, sqlite3, python-dotenv, and jinja2. Set up pytest. In main.py, establish a FastAPI lifespan event that will eventually trigger our database seeding. Do not write the database logic yet, just set up the scaffolding and ensure the app boots successfully on port 8000."

2\. Data Engineering: The B2B Identity Graph (Pandas ETL)
---------------------------------------------------------

> **PROMPT:** "Create a DataGenerator service in /app/data/generator.py. Implement a Faker-based B2B relational generator for 15 target accounts (e.g., Shell, Aramco).
> 
> **Requirements:**
> 
> 1.  Generate 30-50 users per account with standardized seniority (C-Suite, VP/Director, Manager, IC).
>     
> 2.  Generate 90 days of relative-timestamped touchpoints (datetime.now() - timedelta) across Mailchimp, LinkedIn, GA4, and CRM.
>     
> 3.  Implement the 'Bucket' strategy: Golden Path (full match), Partial Match, and Ghosts (anonymous bounces).
>     
> 4.  Write a Pandas ETL function that stitches these together. You MUST use pd.merge(how='outer') to ensure missing touchpoints don't delete accounts. Write the final DataFrame to a local SQLite file (capstone.db) using to\_sql(). Wire this generator to the FastAPI lifespan event."
>     

3\. Business Logic: Service Layer & MCP Tooling
-----------------------------------------------

> **PROMPT:** "Implement the service layer in /app/services/analytics.py. Create the following Python functions using raw SQLite queries via sqlite3 (Do NOT use SQLAlchemy):
> 
> 1.  calculate\_blended\_cpa(): Query total LinkedIn spend divided by total CRM opportunities.
>     
> 2.  get\_account\_penetration(): Group users by company\_name and seniority to return a summarized dictionary.
>     
> 3.  evaluate\_trickle\_threshold(): Identify if a campaign's daily traffic dropped >95% from its peak and sustained that for 7 days. Return a boolean is\_active.
>     
> 4.  simulate\_budget\_shift(channel: str, budget: float): Use historical baseline conversion rates to mathematically project new pipeline volume based on the new budget.
>     
> 
> Format all four of these functions to output JSON Schema definitions so they can be injected into the Gemini API as callable tools."

4\. Frontend: HTMX Integration & Custom Tool States
---------------------------------------------------

> **PROMPT:** "Integrate HTMX into our Jinja2 templates in /app/templates/dashboard.html.
> 
> **Requirements:**
> 
> 1.  Wire up the top header dropdown to toggle between 'Past 7 Days' and 'Past 90 Days' using hx-get="/api/dashboard" with a query parameter.
>     
> 2.  Implement the AI chat interface at the bottom. When a user submits a query, use hx-post="/api/chat".
>     
> 3.  **CRITICAL:** Use hx-indicator or intermediate HTML swapping to display a custom tool-loading state (e.g.,
>     
>     ⚙️ Simulating budget shift...
>     
>     ) while the Python backend processes the LLM request. Do not just use a generic spinner."
>     

5\. AI Integration: Gemini Native SDK & Guardrails
--------------------------------------------------

> **PROMPT:** "Implement the AI router in /app/api/chat.py using the official google-genai SDK (No LangChain).
> 
> **Requirements:**
> 
> 1.  Apply a 'Zero-Math' policy: The LLM system prompt must forbid it from calculating metrics directly; it must rely entirely on the MCP tools defined in step 3.
>     
> 2.  Implement a unified tool-calling loop: When the LLM requests simulate\_budget\_shift, execute the Python function, append the JSON result to the message history, and yield the final LLM response back to the HTMX frontend.
>     
> 3.  Implement graceful degradation: If a Python tool fails (e.g., division by zero), return a hardcoded JSON system message {"error": "tool failed"} to the LLM so it can formulate a polite apology to the user without crashing the UI."
>