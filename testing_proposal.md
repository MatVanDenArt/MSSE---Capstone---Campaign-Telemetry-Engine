# Comprehensive Testing Suite Proposal
**MSSE Capstone Project - Campaign Telemetry Engine**

To achieve maximum points (Score: 5) on the Capstone rubric, we must provide documented evidence of testing methods and CI/CD usage. Given your architecture (FastAPI, HTMX, SQLite, Gemini AI) and your deployment pipeline (GitHub → Render), this proposal outlines a comprehensive 5-tier testing strategy.

## 1. Unit Testing (Core Mathematical Logic)
**Target:** `app/services/analytics_v2.py`
**Tool:** `pytest`

We must mathematically prove to the graders that the calculations powering your dashboard are accurate before the AI even touches them. 
*   **What to test:** **Full coverage of all 16 MCP analytical functions.** This includes:
    *   `calculate_blended_cpa()`: Assert that total spend divided by total conversions yields the correct float.
    *   `get_account_penetration()` & `get_tam_penetration()`: Assert correct percentages based on dummy data.
    *   `evaluate_trickle_threshold()`, `simulate_budget_shift()`, `calculate_share_of_voice()`, `run_attribution_model()`, `get_asset_impact_matrix()`, `get_intent_surge_signals()`, and all other analytical tools exposed to the LLM.
    *   UI Helper functions like `format_pipeline()` and `generate_next_best_actions(campaign_id)`.
*   **Methodology:** We will use a lightweight, in-memory SQLite database populated with a standard set of mock data specifically for the test suite, completely isolating it from your production `capstone.db`.

## 2. LLM & MCP Integration Testing
**Target:** `app/services/llm_rotator.py` & `analytics_v2.py`
**Tool:** `pytest` + `unittest.mock`

*Should we test model availability?* **No.** Directly querying Gemini in a CI pipeline is an anti-pattern (it leads to rate-limit failures, non-deterministic timeouts, and unnecessary token costs).
*   **What to test:** We will test *our system's interaction* with the model. We will use `unittest.mock.patch` to "fake" a response from the Gemini API. 
*   **Methodology:** 
    *   Assert that `generate_strategic_tldr` correctly constructs the `prompt` string and successfully extracts the `.text` property from the mocked response.
    *   Assert that the MCP fallback logic works (i.e., if the mocked API throws a `RateLimitError`, assert that the code gracefully returns the string: *"AI Context Unavailable"* instead of crashing the server).

## 3. API Route Testing
**Target:** `app/api/dashboard_v2.py`
**Tool:** `fastapi.testclient.TestClient`

Since your frontend relies on HTMX, the backend API *is* your presentation layer. If an endpoint fails, the UI breaks.
*   **What to test:** We will programmatically fire `GET` requests to your core endpoints.
    *   `/api/v2/dashboard/overview` -> Assert `status_code == 200` and response contains `<div id="overview-content">`.
    *   `/api/v2/dashboard/investigate-target` -> Pass mock URL parameters and assert the endpoint returns the correctly formatted HTML action card.
*   **Methodology:** The `TestClient` spins up a virtual FastAPI server in milliseconds without occupying a real network port.

## 4. End-to-End (E2E) Frontend Testing (Optional but Recommended)
**Target:** The HTMX DOM
**Tool:** `pytest-playwright`

Because HTMX swaps elements in the DOM dynamically, we need to prove the user journey works in a real browser.
*   **What to test:** A headless Chromium browser will boot up, navigate to the CMO Lobby, click the "Decarbonization" campaign card, and click an alert in the Action Center. 
*   **Methodology:** The test will assert that clicking the trigger successfully renders the Copilot modal on the screen.

## 5. Continuous Integration (GitHub Actions)
**Target:** `.github/workflows/ci.yml`
**Tool:** GitHub Actions

This is the final piece to satisfy the *"collaborative software engineering tools, including CI/CD tools"* rubric requirement.
*   **The Pipeline:** We will commit a YAML file that tells GitHub to automatically run all the `pytest` suites every time a team member opens a Pull Request or pushes to `main`. 
*   **Render Integration:** Render will be configured to "Wait for CI to pass" before deploying. If a teammate accidentally breaks an MCP function, the GitHub Action will fail, and Render will block the deployment, protecting your live environment.

---

### Implementation Plan
If this proposal aligns with your vision, I can execute it in the following phases:
1.  Setup the `tests/` directory and configure `pytest`.
2.  Write the Unit, API, and LLM Mock tests (covering all 16 MCP tools).
3.  Write the GitHub Actions `ci.yml` file.
