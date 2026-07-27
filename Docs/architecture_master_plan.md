
# Master Architecture Plan: Wood Group Campaign Telemetry Engine (MSSE Capstone)

## 1. System Overview & Capstone Context
This project is an MSSE Capstone deliverable simulating a B2B marketing telemetry engine for the "Wood Group". The system aggregates cross-platform campaign data (simulated CRM, Mailchimp, LinkedIn, GA4) into a unified dashboard and features an AI-driven chat interface for analytical queries.

### Key Capstone Deliverables Embedded:
*   Deployed application via Docker on Render (Free Tier).
*   GitHub Repository with CI/CD Actions (shared with quantic-grader).
*   Agile Task Board (Trello).
*   Comprehensive Design & Testing Document (derived from this plan).
*   15-20 Minute Final Video Demonstration.

## 2. Technology Stack & Architectural Patterns
To satisfy the rubric's requirement for well-designed code, the backend will strictly adhere to separation of concerns using established software design patterns.

*   **Backend Framework:** Python (FastAPI). Chosen for native async support, Pydantic validation, and excellent integration with frontend HTMX.
*   **Database:** SQLite. Used for rapid prototyping, referencing, and mathematical benchmarking.
*   **Frontend:** HTML / Tailwind CSS / Vanilla JS / HTMX. Keeps the client lightweight and avoids React build-step complexities while enabling dynamic, asynchronous UI updates.
*   **AI Engine:** Google Gemini API (via Native SDK, No LangChain).

### Implemented Software Patterns:
*   **Service Layer Pattern:** Business logic (e.g., calculating CPA, identifying bounce rate anomalies) is isolated in "Service" classes. The API endpoints simply call these services, keeping routing files clean.
*   **Repository Pattern:** All SQLite SQL queries and Pandas dataframe manipulations are abstracted into a "Repository" layer. If we ever needed to swap SQLite for PostgreSQL, the business logic wouldn't change.
*   **Model Context Protocol (MCP) Pattern:** AI function calling is strictly defined using JSON schemas. The LLM acts purely as a routing/formatting engine, delegating deterministic math to Python.

## 3. The B2B Synthetic Data Engine (Faker)
To simulate the real world without proprietary data, the system includes a cohesive DataGenerator module powered by Python's Faker library.

### Relational ABM Modeling (Story #6 - Account Penetration):
Generating isolated users doesn't work for B2B. We will use a Top-Down relational generation strategy:
*   **Generate Accounts:** Define 10-15 Target Companies (e.g., Shell, Aramco, Equinor) with specific company_domains.
*   **Generate Users:** Use Faker to generate 20-50 users per company, linking them via company_id and assigning messy, real-world job titles.
*   **Generate Touchpoints:** Assign Mailchimp opens, GA4 visits, and LinkedIn clicks to these specific users.

### Data Freshness (Dynamic Startup Seeding):
To account for Render's free tier (which sleeps when inactive), we use Dynamic Startup Seeding. Upon application startup, a FastAPI lifecycle event checks the exact current date (datetime.now()) and seeds 90 days of synthetic touchpoints leading up to that moment. The data is always fresh for the grader.

## 4. Campaign Lifecycle & "Trickle Traffic" Algorithm
The system must automatically distinguish between Live and Past (Completed) campaigns.

*   **The Problem:** We cannot rely on a "0 traffic" rule, as old emails occasionally get clicked months later (statistical noise/trickle traffic).
*   **The Algorithmic Solution:** The Python backend implements a Trickle Threshold Algorithm. A campaign is automatically flagged as "Past" if its daily touchpoint volume drops by 95% from its peak and sustains that drop for 7 consecutive days.
*   **UI Implementation:** The frontend sidebar separates these into "Active Portfolio" and "Archived Campaigns", allowing users to toggle and view historical data without it skewing live aggregated metrics.

## 5. AI Resilience, Tool Calling, & UX States
Strict handling of the LLM connection is required to prevent hallucinations and provide a premium user experience.

*   **UX-Driven Tool States:** When the LLM decides to call a Python tool, it doesn't just show a generic spinner. The FastAPI backend maps the requested tool to a human-readable state (e.g., simulate_budget_shift triggers the UI message: "📊 Simulating budget scenarios..."). This provides immediate, specific feedback to the user while the heavy Pandas math executes.
*   **Pydantic Guardrails:** All inputs from the LLM to the Python tools are validated via Pydantic models.
*   **Graceful Degradation:** If a tool fails, the backend catches the exception and returns a system message to the LLM. The LLM formulates a polite apology to the user, preventing UI crashes.
*   **Zero-Math Policy:** System prompts explicitly forbid the LLM from calculating ROI, spend, or pipeline metrics. It must use Python tools.

## 6. Testing Strategy (Quantic Rubric Alignment)
*   **Unit Testing (pytest):** Used strictly for the Service Layer. We will test the math behind the MCP tools (e.g., passing a $4,000 budget and asserting the CPA is correct).
*   **Data Validation Testing (Pydantic):** Ensuring the Synthetic Data Engine does not produce Null values for critical primary keys.
*   **Integration Testing (FastAPI TestClient):** Testing the API endpoints to ensure they return valid HTML snippets for HTMX.

## 7. CI/CD, Containerization, and Deployment
*   **Containerization:** A Dockerfile will package the FastAPI application, database initialization, and requirements.txt.
*   **Deployment Option:** Render (Free Tier Web Service).
*   **CI/CD Pipeline (GitHub Actions):** Upon pushing code to main, the pipeline will: Checkout code -> Setup Python -> Run flake8 -> Run pytest -> Ping Render deploy hook.
