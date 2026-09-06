# Campaign Telemetry Engine

An autonomous, agentic AI platform designed to analyze B2B marketing telemetry, evaluate pipeline health, and generate data-backed strategic recommendations for executives. 

Built with a lightweight stack focused on hyper-performance and rapid iteration.

## Tech Stack
* **Backend:** Python 3.10+, FastAPI, Uvicorn
* **Database:** SQLite (Standalone zero-config)
* **Frontend:** HTMX, Alpine.js, Tailwind CSS (via CDN)
* **AI Engine:** Google Gemini Pro / Flash via google-genai SDK
* **Testing:** Pytest (Deterministic mathematical assertions + LLM-as-a-judge payload scoring)

## Project Structure
- /app - The core application codebase
  - /api - FastAPI route handlers (dashboard.py, chat.py)
  - /services - Business logic, SQL execution, and the AI llm_rotator agentic harness
  - /templates - Jinja2 HTML templates broken down by component
  - /data/pipeline - Python ETL scripts that generated the synthetic database
- /tests - Pytest suites ensuring mathematical parity and schema validation
- /scripts - Automation scripts, including the ai_evals_matrix.py LLM Judge harness
- /Docs - Architectural plans, user stories, and structural design documents
- /.cache - Ephemeral JSON caches used for rapid AI response rendering and telemetry tracking

## Setup Instructions

1. **Install Requirements**
   pip install -r requirements.txt

2. **Environment Variables**
   Create a .env file in the root directory:
   GEMINI_API_KEY="your_api_key_here"
   DATABASE_URL="capstone.db"

3. **Run the Server**
   Use FastAPI's development server to run the application with hot-reloading:
   fastapi dev app/main.py

4. **Access the Dashboard**
   Navigate to http://localhost:8000/dashboard in your browser.

## AI Copilot Architecture
This platform does not rely on traditional RAG (Retrieval-Augmented Generation) which suffers from hallucination and mathematical inaccuracies. 

Instead, it utilizes **Abstract Late Binding** via the Model Context Protocol (MCP). The LLM is provided with abstract tools. The Python backend catches these commands, securely queries the SQLite database, mathematically computes the result, and returns a verified JSON payload to the LLM for summarization and UI rendering. This ensures 100% mathematical accuracy while retaining autonomous AI behavior.
