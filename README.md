# Campaign telemetry engine

An autonomous, agentic AI platform designed to analyze B2B marketing telemetry, evaluate pipeline health, and generate data-backed strategic recommendations for executives. 

Built with a lightweight stack focused on hyper-performance and rapid iteration.

## Tech stack
* **Backend:** Python 3.10+, FastAPI, Uvicorn
* **Database:** SQLite (Standalone zero-config)
* **Frontend:** HTMX, Alpine.js, Tailwind CSS (via CDN)
* **AI Engine:** Google Gemini Pro / Flash via google-genai SDK
  **Cache:** Redis primary and local JSON fallback
* **Testing:** Pytest (Deterministic mathematical assertions + LLM-as-a-judge payload scoring)

## Project structure
- **/app** - The core application codebase
  - **/api** - FastAPI route handlers (**dashboard.py**, **chat.py**)
  - **/services** - Analytical facade, SQL execution, LLM key rotator, and MCP tools
  - **/services/mcp_tools** - Modular domain packages exporting 16 analytical functions
  - **/templates** - Jinja2 HTML partials and components for Server-Driven UI
  - **/data/pipeline** - Python ETL scripts that construct the synthetic telemetry database
- **/tests** - Pytest suites ensuring mathematical parity and schema validation
- **/scripts** - Automation scripts, including the **ai_evals_matrix.py** LLM Judge harness
- **/docs** - Architectural plans, and structural design documents
- **/.cache** - Ephemeral caches for rapid AI response rendering and telemetry tracking


## Documentation
  - [design_and_testing.md](design_and_testing.md): Comprehensive breakdown of the system architecture, caching strategy, and 5-tier testing approach.  

## Discovery and user stories
  - **Miro board**: https://miro.com/app/board/uXjVHt5PIk4=/?share_link_id=556611025724 
  - [discovery_and_user_stories.md](docs/discovery_and_user_stories.md): Core project requirements, B2B telemetry pain points, and persona-driven user stories.

## Project management
  - **Trello board**: https://trello.com/b/rDaAjrNu/capstone-marketing-telemetry-engine

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

## Live demo on Render
   https://msse-capstone-campaign-telemetry-engine.onrender.com/

## System architecture & codebase overview

The platform is built on a modular, decoupled architecture where each layer maintains clean separation of concerns:

### 1. Application entrypoint & infrastructure (app/main.py)
- Bootstraps FastAPI with lifespan event management for startup/shutdown cycles.
- Mounts static asset directories (**/static**) and configures Jinja2 template rendering.
- Handles campaign lobby routing (**/lobby**), root redirection (**/**), and container health check probes (**/health**).

### 2. Presentation & routing layer (app/api/dashboard.py)
- Implements Server-Driven UI (SDUI) using HTMX attributes (**hx-get**, **hx-post**, **hx-swap**) for dynamic DOM swaps without client-side bundle compilation.
- Serves modular dashboard tab partials:
  - **Overview (**/dashboard/overview**)**: High-level benchmarks, trajectory timeline, TAM penetration, and share of voice.
  - **Performance (**/dashboard/performance**)**: Asset impact matrix, fatigue detection, and engagement spike/bounce alerts.
  - **Audience (**/dashboard/audience**)**: Account penetration, buying committee distributions, and priority sales target follow-ups.
- Houses modal drilldowns and D3/vis visualization feeds (**/channel-roi-data**, **/topic-clusters**, **/abm-data**, **/asset-personas**).

### 3. AI copilot & agentic system (app/api/chat.py)
- Provides conversational telemetry analysis, automated action triggers, and agentic workflows.
- **Session isolation**: Partitioned per user via signed **cte_session** cookies, backed by a dual-tier storage strategy (Redis primary on Render, local JSON fallback for dev).
- **Zero-math policy**: Enforces mathematical precision by forbidding the model from calculating financial figures directly; all metrics are computed via backend MCP tools.
- **SSE streaming**: Dispatches chat requests to an asynchronous Server-Sent Events stream (**/api/chat/stream/{task_id}**) for live progress indicators.
- **Loop guards**: Tracks tool call signatures to detect and break infinite repetition loops.

### 4. LLM rotator & tool registry (app/services/llm_rotator.py)
- **KeyManager**: Round-robin API key rotation with a 60-second cooldown penalty box to mitigate Google Gemini rate limits (HTTP 429).
- **Dual-tier response caching**: SHA-256 prompt hashing with Redis primary (24h TTL) and local file fallback (**.cache/llm_cache.json**).
- **Tool registry**: Canonical Gemini Tool declarations (**mcp_tools**) mapped to executable Python callables (**tool_functions**).

### 5. Analytical facade & service layer (app/services/analytics.py)
- Serves as the central data facade over the multi-channel SQLite database tables (**ga4_events**, **mailchimp_events**, **linkedin_events**, **crm_users**, **crm_opps**, **content_metadata**).
- Manages connection lifecycles per function call and enforces standardized timeframe filtering (**timeframe=0** for All-Time).
- Provides anomaly detection algorithms:
  - **get_high_bounce_asset**: Flags assets with >60% bounce rate on min. 10 sessions.
  - **get_spiking_asset**: Detects content where recent 7-day velocity exceeds 1.5× the prior 7-day window.
  - **get_stalled_account**: Identifies accounts with ≥2 engaged contacts silent for >14 days.
- Eliminates N+1 query patterns in **get_asset_personas** via a 2-query batched UNION execution.

### 6. Model context protocol (MCP) domain tools (app/services/mcp_tools/)
Exports 16 granular analytical tools organized across 4 domain packages, empowering the AI Copilot to query live telemetry:
- **Financial analytics** (**financial.py**):
  - **calculate_blended_cpa**: Blended media spend (LinkedIn + Email + Web) vs Closed Won contracts.
  - **simulate_budget_shift**: Counterfactual budget reallocation modeling.
  - **get_executive_pipeline_kpis**: High-level spend, pipeline value, and contract conversions.
  - **get_budget_pacing**: Daily burn rates, pacing health, and runway projections.
  - **run_attribution_model**: Multi-touch attribution modeling (first-touch, last-touch, linear, time-decay).
- **ABM & audience analytics** (**abm_audience.py**):
  - **get_account_penetration**: Account-level engagement grouped by seniority tier.
  - **get_tam_penetration**: Total Addressable Market coverage vs engaged accounts.
  - **map_buying_committee**: Committee member persona mapping and coverage gap discovery.
  - **get_intent_surge_signals**: 48-hour velocity spikes indicating urgent sales opportunities.
  - **get_user_journey**: Chronological cross-channel touchpoint history for an individual user.
- **Asset performance & health** (**asset_performance.py**):
  - **evaluate_trickle_threshold**: Detects traffic decay (>95% drop sustained for 7 days).
  - **get_asset_impact_matrix**: Composite scoring of assets based on engagement and pipeline influence.
  - **compare_asset_baselines**: Content performance benchmarking against portfolio averages.
  - **calculate_share_of_voice**: Brand impression and click dominance across channels.
- **Generative content synthesis** (**generative.py**):
  - **generate_ab_test_variants**: Synthesizes structured A/B copy variants (Control, Variant A, Variant B) with testing rationales.
  - **draft_outreach_sequence**: Tailors a 3-step sales cadence (Email -> LinkedIn InMail -> Email) based on observed intent topics.

### 7. Synthetic data generation pipeline (**app/data/pipeline/**)
Constructs a deterministic, production-scale B2B marketing telemetry dataset (**capstone.db**) via a 5-stage ETL pipeline:
- **config.py**: Central configuration defining 15 Fortune 500 target accounts (Shell, Aramco, BP, Chevron, etc.), seniority tiers, and persona distributions.
- **01_generate_crm.py**: Generates synthetic B2B buying committee members, CRM accounts, and baseline opportunity lifecycles using Faker.
- **02_generate_baseline_traffic.py**: Simulates organic and baseline web traffic (GA4), outbound newsletter sends/opens (Mailchimp), and sponsored campaign impressions/clicks (LinkedIn).
- **03_simulate_abm_journeys.py**: Injects realistic marketing scenarios—stalled accounts, cross-department expansions, creative fatigue, and intent topic surges.
- **04_etl_load.py**: Combines baseline and ABM event streams, applies data cleansing, and loads tables into SQLite.
- **05_create_indices.py**: Adds covering B-tree indices on high-cardinality foreign keys (**campaign_id**, **user_id**, **account_id**, **timestamp**) for sub-millisecond query performance.
- **build_database.py**: Master CLI orchestrator executing stages 1 through 5 sequentially with execution timers and status logging.


