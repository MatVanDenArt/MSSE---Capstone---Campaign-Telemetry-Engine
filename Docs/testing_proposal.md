# Comprehensive Testing Suite Proposal
**MSSE Capstone Project - Campaign Telemetry Engine**

To achieve maximum points (Score: 5) on the Capstone rubric, we must provide documented evidence of testing methods and CI/CD usage. Given your architecture (FastAPI, HTMX, SQLite, Gemini AI) and your deployment pipeline (GitHub -> Render), this proposal outlines a comprehensive 5-tier testing strategy, updated to specifically address the unique challenges of Agentic AI and the Model Context Protocol (MCP).

## 1. Unit Testing & Data Boundaries (Core Logic)
**Target:** `app/services/analytics.py`
**Tool:** `pytest`

We must mathematically prove to the graders that the calculations powering your dashboard are accurate before the AI even touches them, and that data boundaries are strictly enforced.
*   **What to test:** 
    *   **Full coverage of all 16 MCP analytical functions.** (`calculate_blended_cpa()`, `simulate_budget_shift()`, `get_asset_impact_matrix()`, etc.).
    *   **Data Boundary Authorization:** Ensure every MCP tool function strict-checks the `campaign_id` parameter against the authorized user session context, preventing the AI from cross-campaign data leakage.
*   **Methodology:** We will use a lightweight, in-memory SQLite database populated with a standard set of mock data specifically for the test suite, completely isolating it from your production `capstone.db`.

## 2. LLM, MCP Integration & Fuzz Testing
**Target:** `app/services/llm_rotator.py` & `analytics.py`
**Tool:** `pytest` + `unittest.mock`

Directly querying Gemini in a CI pipeline is an anti-pattern. Instead, we test *our system's interaction* with the model and its resilience to AI hallucinations.
*   **What to test:** 
    *   **MCP Contract Testing:** Dynamically assert that every parameter described in the `mcp_tools` JSON schema perfectly matches the parameter names, types, and defaults of the actual Python function signatures in `analytics.py`. This prevents "Schema Drift".
    *   **Negative Parsing / Hallucination Checks:** Mock *bad* LLM responses (hallucinated tools, missing JSON brackets, wrong data types) and assert that our backend parser handles them gracefully without throwing 500 Server Errors.
    *   **State Rehydration:** Generate a mock AI Action payload, pass it through the SQLite insertion function, immediately query it back, and assert that the rehydrated dictionary matches the original structure required by the Jinja template.

## 3. Offline LLM Evaluations (Reasoning Quality)
**Target:** Gemini 3.6 Flash reasoning logic
**Tool:** `pytest --run-evals` (Manual Trigger)

Unit tests check if the math is right, but they don't check if the AI is *smart*.
*   **What to test:** We need an offline suite (not run on every PR to save costs) that feeds the live LLM standard datasets (e.g., a "Fatigued Campaign" dataset) and asserts that the LLM's response *always* chooses the correct MCP tool (e.g., `get_asset_fatigue`).
*   **Methodology:** This guarantees that as we tweak system prompts, we don't inadvertently "dumb down" the LLM's tool selection logic.

## 4. API Route Testing
**Target:** `app/api/dashboard.py`
**Tool:** `fastapi.testclient.TestClient`

Since your frontend relies on HTMX, the backend API *is* your presentation layer. If an endpoint fails, the UI breaks.
*   **What to test:** We will programmatically fire `GET` requests to your core endpoints.
    *   `/api/dashboard/overview` -> Assert `status_code == 200` and response contains `<div id="overview-content">`.
    *   `/api/dashboard/action-center` -> Assert HTMX lazy-loading endpoints return valid HTML fragments.
*   **Methodology:** The `TestClient` spins up a virtual FastAPI server in milliseconds without occupying a real network port.

## 5. Continuous Integration (GitHub Actions)
**Target:** `.github/workflows/ci.yml`
**Tool:** GitHub Actions

This is the final piece to satisfy the *"collaborative software engineering tools, including CI/CD tools"* rubric requirement.
*   **The Pipeline:** We will commit a YAML file that tells GitHub to automatically run all standard `pytest` suites every time a team member opens a Pull Request or pushes to `main`. 
*   **Render Integration:** Render will be configured to "Wait for CI to pass" before deploying. If a teammate accidentally breaks an MCP function signature, the GitHub Action will fail, and Render will block the deployment, protecting your live environment.

---

### Implementation Plan
If this proposal aligns with your vision, I can execute it in the following phases:
1.  Setup the `tests/` directory and configure `pytest`.
2.  Write the MCP Contract, LLM Fuzzing, and Artifact Rehydration tests (`test_mcp_contracts.py`, `test_llm_parsers.py`).
3.  Write the core Unit and API tests.
4.  Write the GitHub Actions `ci.yml` file.
