# Campaign telemetry engine

An autonomous, agentic AI platform designed to analyze B2B marketing telemetry, evaluate pipeline health, and generate data-backed strategic recommendations for executives. 

Built with a lightweight stack focused on hyper-performance and rapid iteration.

## Tech stack
* **Backend:** Python 3.10+, FastAPI, Uvicorn
* **Database:** SQLite (Standalone zero-config)
* **Frontend:** HTMX, Alpine.js, Tailwind CSS (via CDN)
* **AI Engine:** Google Gemini Pro / Flash via google-genai SDK
* **Testing:** Pytest (Deterministic mathematical assertions + LLM-as-a-judge payload scoring)

## Project structure
- /app - The core application codebase
  - /api - FastAPI route handlers (dashboard.py, chat.py)
  - /services - Business logic, SQL execution, and the AI llm_rotator agentic harness
  - /templates - Jinja2 HTML templates broken down by component
  - /data/pipeline - Python ETL scripts that generated the synthetic database
- /tests - Pytest suites ensuring mathematical parity and schema validation
- /scripts - Automation scripts, including the ai_evals_matrix.py LLM Judge harness
- /docs - Architectural plans, and structural design documents
- /.cache - Ephemeral JSON caches used for rapid AI response rendering and telemetry tracking

## Documentation
  - **`design_and_testing.md`**: Comprehensive breakdown of the system architecture, caching strategy, and 5-tier testing approach.  

## Discovery and user stories
  - **`Miro board`**: https://miro.com/app/board/uXjVHt5PIk4=/?share_link_id=556611025724 
  - **`discovery_and_user_stories.md`**: Core project requirements, B2B telemetry pain points, and persona-driven user stories.

## Project management
  - **`Trello board`**: https://trello.com/b/rDaAjrNu/my-trello-board

## Setup instructions

1. **Install requirements**
   pip install -r requirements.txt

2. **Environment variables**
   Create a .env file in the root directory:
   GEMINI_API_KEY="your_api_key_here"
   DATABASE_URL="capstone.db"

3. **Run the server**
   Use FastAPI's development server to run the application with hot-reloading:
   fastapi dev app/main.py

4. **Access the dashboard**
   Navigate to http://localhost:8000/dashboard in your browser.




## AI copilot architecture
This platform does not rely on traditional RAG (retrieval-augmented generation) which suffers from hallucination and mathematical inaccuracies. 

Instead, it utilizes **abstract late binding** via the model context protocol (MCP). The LLM is provided with abstract tools. The Python backend catches these commands, securely queries the SQLite database, mathematically computes the result, and returns a verified JSON payload to the LLM for summarization and UI rendering. This ensures 100% mathematical accuracy while retaining autonomous AI behavior.
