Antigravity Master Runbook (A-to-Z Prompts)
===========================================

This document contains the exact sequence of prompts you will feed into Antigravity. Do not paste them all at once. Paste them one by one, wait for Antigravity to write and verify the code, and then move to the next.

Phase 0: Context Initialization
-------------------------------

**PROMPT 0 (The Context Seed):**

> "We are building the 'Wood Group Campaign Telemetry Engine,' a B2B marketing dashboard for my MSSE Capstone project. I have the architecture completely planned. We will use FastAPI, SQLite, Pandas for ETL, and HTMX for the frontend. We are implementing a strict Service/Repository pattern and will use the native Gemini API (NO LangChain) with MCP-style tool calling. Do not write any code yet. Just acknowledge you understand these strict constraints and are ready to begin Sprint 1."

Phase 1: Setup & Synthetic Data Engine (Sprint 1)
-------------------------------------------------

**PROMPT 1 (Infrastructure):**

> "Initialize the FastAPI project. Create the Domain-Driven folder structure: /app (with main.py, /api, /services, /data, /templates), /tests, a Dockerfile, and requirements.txt. The requirements must include fastapi, uvicorn, pandas, faker, google-genai, and pytest. Write the baseline main.py to simply serve a "Hello World" on port 8000. Do not write the database logic yet."

**PROMPT 2 (The Faker ETL Pipeline):**

> "In /app/data/generator.py, create a DataGenerator class using Faker. It must generate 15 target B2B accounts (e.g., Shell, Aramco) and 30-50 users per account. Generate 90 days of relative touchpoints across Mailchimp, GA4, LinkedIn, and CRM (Opportunities). Crucially, write a Pandas ETL function that uses pd.merge(how='outer') to stitch anonymous GA4 sessions to known users based on form fills. Output this final DataFrame to capstone.db in SQLite via to\_sql(). Wire this generator to run automatically on FastAPI's startup lifespan event."

Phase 2: UI & Core Business Logic (Sprint 2)
--------------------------------------------

**PROMPT 3 (The HTMX Dashboard):**

> "I have an HTML wireframe for the dashboard. Create /app/templates/dashboard.html and set up FastAPI to serve it via Jinja2Templates. Once served, update the template to use HTMX. Wire up the top header dropdown to toggle between 'Past 7 Days' and 'Past 90 Days' using hx-get='/api/dashboard/metrics' to fetch fresh data without a page reload."

**PROMPT 4 (The Service Layer & Algorithms):**

> "In /app/services/analytics.py, write the core Python business logic using raw SQLite queries. Write calculate\_blended\_cpa() (LinkedIn Spend / CRM Opps) and get\_account\_penetration() (grouping users by company and seniority). Also, write the evaluate\_trickle\_threshold() algorithm: it must query SQLite and return False (Completed) if a campaign's daily traffic dropped >95% from its peak for 7 consecutive days."

Phase 3: AI Chat & MCP Tools (Sprint 3)
---------------------------------------

**PROMPT 5 (The MCP Tool Registry):**

> "We need to expose our Python functions to the Gemini LLM. In /app/services/mcp\_tools.py, create a JSON Schema definition for simulate\_budget\_shift(channel, budget). This Python function must query historical conversion rates from SQLite and mathematically project new pipeline volume. Ensure it is strictly typed using Pydantic to prevent the LLM from passing invalid arguments."

**PROMPT 6 (The AI Router & Custom UX):**

> "In /app/api/chat.py, implement the native Gemini API chat endpoint. Implement a 'Zero-Math Policy' system prompt (the LLM cannot do its own math). When the LLM requests the simulate\_budget\_shift tool, intercept it. Send an intermediate HTMX string back to the frontend:
> 
> ⚙️ Simulating budget shift against historical GA4 data...
> 
> . Then, execute the Python function, append the result, and stream the final LLM response to replace the loading state."

Phase 4: Capstone Testing & QA (Crucial for Grading)
----------------------------------------------------

**PROMPT 7 (Unit & Integration Testing):**

> "We need to satisfy the Capstone testing rubric. In the /tests folder, write pytest suites. First, write a test for /app/services/analytics.py mocking the SQLite database to ensure the CPA math is exactly correct. Second, write a Pydantic validation test for the DataGenerator to ensure no primary keys are generated as Null. Third, use FastAPI TestClient to ensure the main endpoint returns a 200 status code."

**PROMPT 8 (Graceful Error Handling):**

> "Update the AI router to handle backend tool failures. If simulate\_budget\_shift throws a Python exception (e.g., division by zero due to lack of mock data), catch it. Inject a system message into the LLM context stating 'Tool Failed', so the LLM can generate a polite apology to the user without crashing the FastAPI application."