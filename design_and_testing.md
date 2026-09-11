# Campaign telemetry engine: Design and architecture document

This document outlines the core architectural choices, rationale, and design systems implemented for the campaign telemetry engine project. 


## 1. Project rationale: Solving the actionability gap

### The market gap
Imagine a chief marketing officer at a B2B firm asking: "We spent $150,000 on the 'Decarbonisation' campaign over the last 12 months. Did it actually help us win the $10M Equinor contract?"

In enterprise B2B marketing, which is characterized by 18-month sales cycles and complex buying committees, answering this is difficult. Marketers often use analytics tools designed for B2C transactions, forcing them to pull up disconnected screens: Google Analytics for web traffic, Mailchimp for emails, LinkedIn for ad clicks, and Salesforce for closed deals. 

When data is this fragmented, it's easy to lose sight of the big picture and default to reporting vanity metrics rather than actual pipeline influence.

### The team gap
Historically, extracting cross-channel insights required dedicated data analysts interpreting and consolidating data from multiple siloes, or marketers spending weeks mastering BI tools. This creates an operational bottleneck between seeing the data and deciding on the next best action.

### The solution: Combining prescriptive analytics and agentic AI
This capstone project shifts the focus from purely descriptive analytics to actionable, AI-assisted insights. The **Campaign telemetry engine** acts as an automated system that connects these distinct data sources to stitch user **journeys** together. 

Rather than requiring the user to hunt through complex graphs, the system programmatically surfaces anomalies (e.g., asset fatigue) via an Action Center. The integrated AI Copilot then uses this context to propose corrective actions.

### Usability and target audience
This platform is designed to aid decision makers who need immediate, actionable insights:

- **CMO overview:** An executive dashboard providing marketing effectiveness metrics (e.g., pipeline velocity, blended CPA) without requiring deep dives into individual tactics.
- **Campaign managers:** Unlocks tactical agility. The omnichannel asset matrix flags "asset fatigue", allowing for budget reallocation before ad spend is wasted.
- **Sales leadership:** Bridges the marketing-sales divide. The account penetration view flags high-intent targets, helping sales directors draft highly contextualized outreach.

### The capstone justification
This project was selected because it integrates three core engineering challenges:

1. **AI orchestration with constraints:** Implementing an MCP-like approach to force an LLM to rely strictly on deterministic Python functions, demonstrating how AI can be grounded in actual financial and performance data.
2. **Server-driven UI:** Building a UI that dynamically injects interactive AI analysis directly into the user's workflow using HTMX and FastAPI.
3. **Data stitching:** Architecting the logic to connect anonymous web cookies to known CRM contacts across a fragmented landscape via a robust simulation.

The following sections detail the architectural decisions, the data simulation engine, the dual-tier caching strategy, and the iterative evaluation harness used to validate and harden the system.

## 2. The user experience: Data visualisation, action centre, and copilot

The user experience is built on a deliberate three-pillar philosophy:

1. **Data visualisation:** 
   High-density, scannable graphs and sections present unified telemetry. The visual elements (colours, sparklines, spacing) are constrained to convey health and channel identity quickly without overwhelming the user.
2. **The action centre:** 
   An automated, dynamic to-do list (priority actions) powered by the backend analytics engine. Instead of forcing the user to hunt for insights, the system mathematically detects trends and anomalies (e.g., calculating when an asset's traffic drops by 90% from its peak) and queues them up as actionable alerts.
3. **The AI copilot:** 
   An interactive assistant seamlessly embedded alongside the data. When the user interacts with an action centre item, the copilot guides them through execution—whether that means drafting a follow-up email sequence, analysing a channel mix, or suggesting asset rotations.

## 3. Data simulation setup and logic

To effectively test the campaign telemetry engine and develop the AI copilot without relying on sensitive or static client data, the project employs a code-driven data simulation pipeline. Building real-time integrations with live GA4, Salesforce, and LinkedIn APIs was not possible due to operational sensitivity of the required data. The simulation cleanly abstracts the data complexity while aspiring to maintain the mathematical realism. 

The pipeline is orchestrated by a single master script (build_database.py), which runs four distinct stages sequentially to produce a clean, populated SQLite database (capstone.db):

### 1. CRM foundation (01_generate_crm.py)
- **Account generation**: Uses the Faker library to generate thousands of realistic B2B professionals, grouping them into specific target accounts (e.g., "Shell", "BP"), seniority levels, and job roles.

### 2. Baseline traffic generation (02_generate_baseline_traffic.py)
- **Background noise**: Injects randomised, standard traffic across email, LinkedIn, and web for legacy campaigns (e.g., Gastech) to simulate realistic marketing baseline noise.

### 3. The ABM simulation engine (03_simulate_abm_journeys.py)
This is the core mathematical engine. Rather than generating random noise, this script simulates highly realistic, **18-month cross-channel buyer journeys** for strategic account-based marketing (ABM) campaigns.
- **Campaign burst logic**: Events are mathematically clustered around specific marketing "bursts" (e.g., a webinar drop, a LinkedIn campaign launch) to simulate realistic traffic spikes and decay.
- **Fatigue modeling**: The script intentionally degrades traffic to specific older assets over time to mathematically trigger the "Asset fatigue" anomalies that the action center relies on.
- **In-memory alignment**: Crucially, the script guarantees logical alignment. It ensures that a CRM "Opportunity created" event mathematically aligns with a recent campaign burst, enforcing the causal relationship between marketing touches and sales pipeline.

### 4. Identity resolution & ETL (04_etl_load.py)

In enterprise B2B marketing, the attribution chain almost always breaks at the very first touchpoint because prospective buyers research anonymously. A technical lead at Shell might click a sponsored LinkedIn post, browse product whitepapers, and leave without submitting an email. Three weeks later, they might return via a direct link or click an email sequence, finally completing a gated content download. 

If an analytics engine treats that first ad click as an isolated anonymous visit and the later download as a brand-new user, multi-touch attribution is fundamentally flawed: the paid campaigns appear to produce zero pipeline, and the first-touch attribution is blind.

To solve this, the identity resolution stage implements a deterministic identity graph and retroactive cookie stitching engine using Pandas, mimicking the core deduplication logic of enterprise customer data platforms (CDP).

![Identity resolution](/docs/identity_resolution.jpg)

#### How the resolution pipeline works

As shown in the architecture flow above, incoming telemetry flows into the ETL from two distinct operational channels:

1. **Deterministic inbound / known contacts:**
   When a known CRM lead clicks a link in a Mailchimp campaign, unique URL parameters pass their verified identity directly into the website telemetry. The GA4 session captures **user_id_captured: 101**, which maps immediately to **j.doe@shell.com** in the CRM system.
2. **Anonymous inbound / paid media:**
   When an enterprise buyer clicks a LinkedIn Ad, they arrive on the site with only UTM parameters and a transient client cookie (**cookie_id: 12345**). At this stage, **user_id_captured** is **NULL**.
3. **The conversion event / the identity bridge:**
   When that anonymous visitor eventually converts—such as filling out a form to download a decarbonisation whitepaper—the browser records a conversion event capturing **user_id_captured: 101**. This creates the critical link between the anonymous cookie and the CRM record for Jane Doe at Shell Plc.
4. **Retroactive cookie stitching / lookback resolution:**
   Rather than only tagging *subsequent* visits, the ETL script extracts every unique **cookie_id, user_id_captured** pair and performs a backward-looking merge across the entire GA4 session history. It retroactively assigns **user_id: 101** to all historical sessions associated with **cookie_id: 12345**.   
   Next, it joins the LinkedIn ad events against this resolved session map via **cookie_id** / **click_id**. In a single pass, the initial paid social ad click—which had been completely anonymous weeks prior—is stitched into Jane Doe's unified customer journey.
5. **Preserving unconverted traffic:**
   Not every visitor converts. An ad click that bounces immediately or browses without identifying themselves is retained via an outer join on **cookie_id**. This allows the engine to accurately report overall channel ad spend, cost per click, and bounce rates without contaminating CRM account rosters with phantom users.

By performing this resolution step before loading data into SQLite, downstream tools like **get_user_journey** and **run_attribution_model** can query a single, unbroken chronological timeline from first anonymous ad touch to closed-won deal.

### 5. Post-ETL optimisation & anti-pattern purge (05_create_indices.py)
To ensure the analytical MCP functions can query the embedded database in milliseconds, a non-destructive indexing strategy was implemented.
- **Drop-load-rebuild pattern**: The ETL pipeline intentionally generates the database without indices (maximising bulk insert speed). Immediately after the data is loaded, 05_create_indices.py applies 11 highly targeted B-Tree indices to critical foreign keys and filter columns.
- **Index-aware filtering**: Queries explicitly use exact matches.

This clean, 5-step modular architecture ensures that the analytics service can seamlessly track a single user across an email click, a social ad view, and subsequent web page interactions. This programmatic simulation allows the frontend visualisations and AI interpretations to simulate user journeys against complex, multi-touch attribution scenarios similar to real-world marketing scenarios.

## 4. LLM model selection & adaptability

The intelligence layer of the copilot is primarily driven by Google's **gemini-3.8-flash**, backed by an automated fallback cascade down to **gemini-3.6-flash** and **gemini-3.5-flash** for robusness of the free tier solution. Choosing this model family and structuring this specific multi-tier architecture emerged from analysing the actual demands of my agentic workflow against real-world API rate limits, latency profiles, and cost structures.

### The model landscape: Why Flash over Pro or local SLMs?
When integrating an LLM into an analytical system, the temptation is often to reach for the most powerful frontier model available under the assumption that "smarter is always better." In my architecture, however, that assumption is incorrect for the following reasons:

1. **Division of cognitive labour:** In my MCP architecture, I deliberately prohibit the LLM from performing raw arithmetic or database joins. All financial formulas (e.g., blended CPA, budget pacing run-rates) and data queries run deterministically in Python against indexed SQLite tables in sub-millisecond time. The model's responsibility is purely synthesis: reading verified JSON outputs, extracting meaningful business patterns, and explaining them to a marketing executive. Paying the latency and cost penalty of a frontier reasoning model simply to summarise structured JSON is an would be highly inefficient.
2. **Interactive UI latency:** The copilot lives in a server-driven HTMX interface with real-time SSE streaming. A user clicking "Analyse asset fatigue" expects the system to acknowledge and stream advice quickly, providing real-time feedback. Frontier "Pro" models typically exhibit higher time-to-first-token (TTFT) and slower generation speeds, which degrades the user experience into an awkward waiting game. Flash models, by contrast, routinely respond in under 800ms.
3. **Quota constraints on the free tier:** For a capstone evaluation and live cloud demonstration (hosted on Render), relying on Google AI Studio's free tier is an operational necessity. On this tier, Pro models are throttled to a restrictive 2 Requests Per Minute (RPM) and 50 Requests Per Day (RPD). In my application, where a single user interaction can trigger a multi-turn tool calling sequence (inspecting committee members, checking asset fatigue, and recursively drafting an email sequence), a Pro model would exhaust the daily quota after barely three or four queries. In contrast, Flash family models provide 15 RPM and 1,500 RPD, offering the operational headroom needed for sustained demonstrations and automated evaluation suites.
4. **Why not ultra-light / edge SLMs?** At the other extreme, sub-3B parameter local models (e.g., Gemma-2B, Llama-3.2-1B) struggle significantly with complex function-calling schemas. In early testing, smaller models frequently hallucinated nonexistent parameters or failed to return valid JSON tool calls. The Flash tier represents the exact sweet spot: industrial-grade function-calling reliability combined with high throughput.

### Evaluating gemini-3.8-flash: Benefits and practical drawbacks
Our primary production model is **gemini-3.8-flash**. Operating it across the test suites and interactive sessions highlighted clear strengths alongside distinct operational quirks:

#### Benefits
- **Exceptional tool-calling precision:** Across the 16 analytical MCP tools, **gemini-3.8-flash** demonstrates near-zero parameter hallucination. It consistently infers the correct **campaign_id** and **timeframe** from conversational context and adheres strictly to the OpenAPI-compatible function schemas.
- **1M+ token context headroom:** B2B buyer journeys in my data engine span 18 months of multi-touch events, buying committee rosters, and asset impact matrices. The extensive context window allows us to pass rich, chronological timelines without having to prematurely truncate or build complex chunking pipelines that risk losing causality.
- **Crisp, commercially grounded tone:** Unlike earlier generations that tended toward generic marketing platitudes, 3.8 Flash reliably adopts an executive analytical tone. When asked to evaluate an underperforming asset, it cites specific metrics (e.g., "traffic decayed 84% from peak while CPA escalated to $1,420") and immediately proposes actionable budget reallocation steps.

#### Drawbacks and engineering mitigations
- **Over-eagerness in tool loops:** Flash models can occasionally be over-eager. In multi-turn tool loops, if an initial tool response yields a partial answer, the model sometimes attempts to call the exact same tool with the exact same arguments in the next turn. Left unchecked, this risks burning API quota in an infinite loop. I resolved this vulnerability by implementing an in-memory call signature tracker (**last_call_signature**) inside **app/api/chat.py** that detects duplicate calls and returns an informative break prompt.
- **Formatting drift:** Because the HTMX frontend directly injects backend-rendered HTML into DOM slots, the model must output strictly formatted HTML action buttons. Flash models will occasionally wrap these buttons in markdown code blocks if not firmly instructed. This was addressed through rigid few-shot examples in the system prompt and defensive regex post-processing.
- **Burst quota sensitivity:** Even with 15 RPM, running back-to-back automated evaluations or having two users interact simultaneously can momentarily trigger HTTP 429 (**RESOURCE_EXHAUSTED**) errors. I resolved this vulnerability during testing by implementing a multi-tiered model and api key resilience design.

### AI model abstraction layer
I isolated all LLM interactions within a dedicated service layer (**app/services/llm_rotator.py**) rather than scattering SDK calls across the route handlers.

This abstraction provides flexibility:
- **Centralized schema management**: Updating the tool JSON schemas in one location ensures the LLM adapts to new parameter requirements.
- **Model agnosticism**: The core application passes generic text prompts to the rotator, which handles provider-specific SDK logic. 
- **Future-proofing**: If there is a need to migrate to an open-source local model (such as a self-hosted Llama or Mistral instance), only the adapter inside **llm_rotator.py** needs to be updated.


## 5. AI architecture: The model context protocol (MCP)-like function calling approach

To combat the inherent risk of large language model (LLM) hallucinations when analysing raw data, the AI copilot architecture heavily relies on a model context protocol (MCP)-like approach:

- **Deterministic data anchoring**: The AI does *not* query raw database tables freely, nor does it perform its own mathematical aggregations. Instead, deterministic, strictly tested Python functions run the core mathematical and business logic.
- **Dynamic MCP function calling**: The copilot provides the LLM with structured JSON tool declarations (mcp_tools). When a user submits an analytical query or triggers an **Action center** task, Gemini dynamically selects which tool to invoke. FastAPI intercepts the function_call, executes the corresponding Python function in the modularized app/services/mcp_tools/ package (exposed via the app/services/analytics.py facade) against the SQLite database, and returns the verified JSON payload back to the model via types.Part.from_function_response.
- **Hallucination elimination**: Because the LLM is only tasked with *interpreting*, *prioritising*, and *synthesising* factual context returned by verified Python functions—rather than performing arithmetic or generating unconstrained SQL—financial and performance metrics are mathematically consistent.

### MCP interaction flow
The sequence diagram below illustrates the actual multi-turn execution loop implemented in app/api/chat.py:

![sequence diagram](/docs/sequence_diagram.jpg)

### Accessible python functions (MCP toolset)
The LLM does not have open-ended database access. Instead, it is constrained to the outputs of 16 analytical functions, which strictly scope data using campaign_id and timeframe.

#### 1. Financial & pipeline analytics (app/services/mcp_tools/financial.py)
- **calculate_blended_cpa**(campaign_id, timeframe): Calculates the blended cost per acquisition across channels.
- **simulate_budget_shift**(campaign_id, timeframe): Simulates projected pipeline impact of budget reallocation with fatigue dampening.
- **get_executive_pipeline_kpis**(campaign_id, timeframe): Aggregates hard performance stats for the strategic TLDR.
- **get_budget_pacing**(campaign_id, timeframe): Returns current vs. expected spend pacing and calculates daily run rates.
- **run_attribution_model**(campaign_id, timeframe): Executes specific multi-touch attribution models (first-touch, last-touch, linear, W-shaped).

#### 2. ABM & audience intelligence (app/services/mcp_tools/abm_audience.py)
- **get_account_penetration**(campaign_id, timeframe): Maps engagement to specific CRM target accounts.
- **get_tam_penetration**(campaign_id, timeframe): Calculates total addressable market penetration.
- **map_buying_committee**(campaign_id, timeframe): Maps engaged personas and functional tiers within a target account.
- **get_intent_surge_signals**(campaign_id, timeframe): Identifies 48-hour velocity spikes and surge signals per account.
- **get_user_journey**(campaign_id, timeframe): Traces chronological multi-channel touchpoints for a specific prospect.

#### 3. Asset performance (app/services/mcp_tools/asset_performance.py)
- **evaluate_trickle_threshold**(campaign_id, timeframe): Determines traffic decay over time against peak volume thresholds.
- **get_asset_impact_matrix**(campaign_id, timeframe): Calculates fatigue indices and ROI scores per creative asset.
- **compare_asset_baselines**(campaign_id, timeframe): Isolates performance gaps and statistical deviations between two assets.
- **calculate_share_of_voice**(campaign_id, timeframe): Benchmarks campaign performance and channel dominance against competitors.

#### 4. Generative & outreach (app/services/mcp_tools/generative.py)
- **generate_ab_test_variants**(campaign_id, timeframe): Recommends data-backed A/B test variations tailored to target buyer personas.
- **draft_outreach_sequence**(campaign_id, timeframe): Generates structured multi-step sales outreach sequences based on intent signals.

### Tool execution architecture: Sequential vs. parallel execution
The application supports batching multiple tool execution requests into a single API roundtrip to reduce latency. However, parallel execution introduces an orchestration challenge: an LLM cannot logically chain dependent tools if it calls them simultaneously (for example, attempting to simulate a budget shift before knowing the current pacing shortfall).

To balance low-latency parallel execution with data precision, I implemented **abstract late binding**. Rather than forcing the LLM to guess numeric variables or perform mental math, MCP tools accept declarative string tokens (such as budget="REMAINING_BUDGET"). When the Python backend receives these tokens, it intercepts them, resolves the underlying dependency locally against SQLite, and injects the verified values into the calculation. This prevents arithmetic hallucinations without forcing slow, iterative roundtrips.



## 6. Core technology stack

I chose a lightweight, server-driven architecture to prioritize development speed and performance.

### Backend: FastAPI (Python)
I chose FastAPI over alternatives like Flask or Django due to two specific requirements:
1. **Asynchronous non-blocking I/O:** Essential for handling long-polling LLM API calls and background aggregations concurrently without freezing worker processes.
2. **Native dependency injection:** FastAPI's Depends(get_db) pattern allowed me to manage request-scoped database connection lifecycles in the routing layer cleanly, keeping web framework logic strictly decoupled from analytical math.

### Frontend: HTMX + Alpine.js + Jinja2
To avoid the state-synchronization overhead and build complexity of a full JavaScript SPA (React/Vue), I paired HTMX with Jinja2 server-side rendering. HTMX requests return pure HTML fragments directly into DOM slots, which makes it an ideal transport layer for server-rendered AI chat responses. Alpine.js provides lightweight client-side state for tab switching and Chart.js initialization without requiring a virtual DOM.

### Styling: Tailwind CSS
Tailwind enabled rapid UI iteration directly inside Jinja2 templates, avoiding the maintenance overhead of large external stylesheets while maintaining a consistent visual hierarchy across dense data tables.

### Database: SQLite (Prototype) vs. PostgreSQL (Production)
SQLite was selected for the prototype because of zero-configuration portability: the entire simulated database (capstone.db) packages directly into the repository and container build, enabling immediate local testing and seamless PaaS deployments without database provisioning. 
However, SQLite's file-level write lock represents a deliberate prototype trade-off. For a multi-user enterprise environment ingesting live GA4 and CRM webhooks continuously, the data layer would migrate to managed PostgreSQL (e.g., AWS RDS) to support high-throughput concurrent writes.

### Caching & state management: Redis (with local fallback)
I used Redis (via REDIS_URL) as an in-memory cache to store SHA-256 hashed prompt-response pairs with a 24-hour TTL. This significantly reduces LLM latency and API costs for repeated strategic queries.
To ensure local development works out-of-the-box without requiring a Redis container, I built a graceful fallback mechanism. If REDIS_URL is missing or unreachable, the system automatically falls back to reading and writing to a local llm_cache.json file. The Render deployment utilizes Redis caching, while local environments default to the file fallback.

### Visualization: Chart.js
Chart.js is performant enough to handle multiple mini-charts dynamically initialized inside Alpine blocks.

## 7. Software and architectural patterns

Every engineering decision involves a trade-off, and this project is no different. The following section describes the structural patterns I reached for, explains why they were appropriate for this context, and where I knowingly deviated from textbook ideals in the interest of delivery speed.

### Facade pattern

The MCP toolset is split across four domain modules — financial.py, abm_audience.py, asset_performance.py, and generative.py — each responsible for a distinct analytical area. However, scattering import paths across the codebase creates fragility: if a module is renamed or moved, every consumer breaks independently. To solve this, app/services/analytics.py acts as a **facade**: it re-exports the full toolset from a single, stable surface, so that dashboard.py, chat.py, and the test suite all import from one predictable location regardless of how the underlying modules are organised. 

### Strategy pattern

The AI copilot receives tool call requests from the Gemini model at runtime — and the application must resolve a string tool name (e.g., "map_buying_committee") to an actual Python callable without a chain of if/elif branches. I addressed this using a **tool registry**: a tool_functions dictionary in llm_rotator.py maps every tool name to its corresponding function reference. When the model requests a tool, the execution loop in chat.py looks up the name in this dictionary and calls whatever function it resolves to. The calling code is completely agnostic about which concrete function is invoked. Adding or removing a tool requires a single dictionary entry.

### Adapter pattern

The Google generative AI SDK changed its client API between versions, and maintaining compatibility with both is a practical concern during iterative development. Rather than littering the codebase with version checks, llm_rotator.py wraps each SDK generation in its own thin adapter, exposing a uniform interface to the rest of the application. The decision of which adapter is active is made once at initialisation time. This pattern is what makes the model agnosticism achievable in practice — switching to a different provider or SDK revision requires rewriting only the adapter internals, not the orchestration logic in chat.py.

### Server-sent events

Long-running LLM calls present a specific UX problem: if the backend waits for a complete response before returning anything, the user stares at a blank UI for several seconds. The standard HTTP request-response model is poorly suited to this. The solution I reached for is **server-sent events (SSE)**: when a chat message is submitted, the route handler immediately returns a task_id and a streaming StreamingResponse. The actual LLM work runs inside an event_generator() coroutine, pushing incremental HTML fragments to the browser as they become available. SSE was preferred over WebSockets here because the communication is unidirectional — the server pushes content to the client, not the other way around.

### Server-driven UI

The frontend never fetches raw JSON and then renders it client-side. Instead, every API route in dashboard.py returns a rendered HTML fragment that HTMX swaps directly into a named DOM target. This is a deliberate architectural choice. It means the server owns the presentation logic, templates stay in one place (Jinja2), and the AI copilot's responses — which are already Markdown-rendered HTML on the backend — can be injected into the chat panel as-is without any client-side parsing step. The trade-off is that each UI state change requires a round-trip to the server. Given that the application's primary content is analytically derived (querying SQLite, calling LLM APIs), that round-trip is already necessary, so the penalty is lower than it would be for a purely data-presentation use case.

### The observer pattern

Several components need to communicate without direct coupling. For example, clicking "Explore in detail" on a person card in the Accounts section needs to both open the copilot sidebar and submit a pre-structured query — but the card and the sidebar live in entirely separate parts of the DOM with no shared parent scope. Rather than introducing a global Alpine.js store (which would require coordinated state management across components), I used native browser CustomEvent dispatched on window as an **event bus**. Components that need to signal intent dispatch events (open-chat, open-asset-modal, open-user-modal), and the components that own those UI surfaces listen for them independently. This results in an observer pattern at the frontend layer where emitters and receivers are decoupled by design, and adding a new surface that responds to an existing event requires no changes to the emitter.

### Dependency injection: applied selectively

FastAPI's Depends(get_db) pattern manages request-scoped database connection lifecycles cleanly in the routing layer: connections are opened per-request, injected into the handler, and closed automatically when the response completes. This follows the **unit of work** pattern and prevents connection leaks under concurrent load. However, I have not applied this consistently throughout the codebase. The MCP tool functions in app/services/mcp_tools/ currently manage their own internal connections via direct get_db_connection() calls. This inconsistency exists because cleanly injecting a db parameter into the MCP tools would expose that parameter in the JSON schema visible to the LLM — an unacceptable leak of implementation detail into the tool contract. The resolution (decoupling the schema definitions from the callable implementations) is documented in §11 as a planned architectural action.

### Application factory and lifespan management

app/main.py uses FastAPI's lifespan async context manager which follows the **application factory** pattern: the application object is constructed and its lifecycle managed in one place, with startup and shutdown logic executing predictably within the context manager's scope. For the current capstone deployment, the lifespan handler is lightweight, but this structure means that future startup concerns — connection pool warming, model preloading, scheduled cache invalidation — can be added cleanly without touching route logic.

### Global state as a deliberate prototype shortcut

One pattern choice deserves an honest explanation: app/api/chat.py maintains chat_history and active_chat_tasks as module-level global variables. Every request in the application shares these objects, which means all users share the same conversation history and task queue. This was a deliberate shortcut for a single-user demonstration context — it avoids the complexity of session management while allowing the copilot to maintain context across a multi-turn conversation within a single browser session. In any multi-user deployment, including the live Render instance, two concurrent users would interleave their chat histories. The correct production architecture is a Redis-backed session store keyed by a user ID or signed session token, isolating chat state per user. The shortcut is acceptable for a capstone demonstration; it would need to be resolved before a team-level rollout.



## 8. Deployment strategy & cost implications

### Phase 1: Capstone release (PaaS / Cloud-native)
For the initial capstone release, the application is designed to be deployed via **Render** (Platform-as-a-Service), automated through **GitHub actions**. 
- **Setup**: Pushes to the main branch trigger a GitHub action that tests the application and deploys it directly to Render. The embedded SQLite database (capstone.db) is packaged within the deployment for zero-configuration testing.
- **Cost**: Free. Render's free tiers are sufficient for demonstrating the UI, FastAPI backend, Redis,  and handling lightweight traffic.
- **Limitations**: The SQLite database is ephemeral in containerised cloud environments unless mounted to a persistent disk. This is acceptable for the simulation, but not ultimatley suitable for production.

### Phase 2: Enterprise production (Cloud vs. On-Premises)
Moving beyond the capstone into a production enterprise environment requires architectural shifts, particularly concerning data privacy and scale.

#### Option A: Managed cloud (AWS / Azure / GCP)
- **Architecture**: The application database should migrate from SQLite to a managed PostgreSQL instance (e.g., AWS RDS). The FastAPI application should be deployed via container orchestration (e.g., AWS ECS or Kubernetes). Managed ETL tools (Fivetran/dbt) should be used to ingest real GA4 and CRM data continuously.
- **Cost Implications**:  
  - Database: ~$50-$200/month for a production RDS instance.
  - Compute: ~$50-$100/month for scalable container hosting.
  - LLM API Costs: Highly variable based on token usage. Utilising **gemini-3.8-flash** (with automated fallback down to 3.6 and 3.5) keeps operational costs minimal (fractions of a cent per query), while scaling across a broader organization would require budgeting for continuous token consumption. The application actively minimizes this expenditure through its dual-tier prompt caching layer.
- **Pros**: Infinite scalability, zero hardware maintenance, rapid deployment.

#### Option B: On-Premises / air-gapped deployment
- **Architecture**: For enterprise engineering firms dealing with highly sensitive IP or with highly sensitive customer data, the entire stack can be deployed on internal, on-premises servers. Because the application is fully containerised, it can run on internal Kubernetes clusters.
- **AI adaptation**: The llm_rotator.py abstraction allows the organisation to completely unplug from cloud-based AI providers (Google/OpenAI) and point the copilot to an internally hosted, open-source LLM (e.g., A marketing optimised model running via Ollama on a local GPU).
- **Cost implications**: High CapEx, Low OpEx.
  - Hardware: Significant upfront capital expenditure ($8-12k) for dedicated server equipped with high-VRAM GPUs (e.g., NVIDIA A100s or multiple RTX 4090s) necessary to run LLMs locally.
  - Maintenance: Requires dedicated internal DevOps/IT personnel.
  - API Costs: $0. Once the hardware is purchased, infinite AI queries can be made without paying token fees.
- **Pros**: Absolute data sovereignty. Zero risk of proprietary CRM or pipeline data leaking to public cloud AI providers.

## 9. Testing strategy

Testing an agentic AI-integrated telemetry engine introduces specific set of challenges not traditionally encountered in web application testing. While standard applications rely on deterministic unit and E2E testing, integrating an autonomous LLM via the MCP introduces non-deterministic behavior, schema drift, and hallucination risks.

To catch different categories of failure, I structured the testing into seven distinct layers using pytest and GitHub Actions.

### 1. Unit testing & data boundaries (Core logic)
Before the AI model is allowed to reason about the data, the underlying mathematical calculations must be proven accurate.
- **Approach**: The tests/conftest.py suite utilises a lightweight, in-memory SQLite database populated with a standardised set of mock campaign data, completely isolating the test environment from the production capstone.db.
- **Coverage**: The tests/test_unit.py suite strictly asserts the mathematical outputs and data types of the core analytical functions (e.g., calculate_blended_cpa, get_tam_penetration). It also enforces data boundary, ensuring tools strictly adhere to campaign_id and timeframe session context to prevent cross-campaign data leakage.

### 2. MCP contract testing (Preventing schema drift)
As the AI model relies on a strictly defined JSON schema (mcp_tools) to understand the backend Python tools it can call, "schema drift" is a fatal risk. 
- **Approach**: The tests/test_mcp_contracts.py suite programmatically iterates over every tool defined in the JSON schema. It utilises Python's inspect.signature to read the actual backend function signatures exported through app/services/analytics.py and implemented within the modular app/services/mcp_tools/ domain modules.
- **Coverage**: It mathematically asserts that every tool listed in the schema actually exists as a callable function, and that the parameters promised to the LLM exactly match the parameters the Python function accepts, making schema drift impossible.

### 3. MCP integration & data parity testing (Deterministic)
While unit tests prove the core math, integration tests are required to ensure the backend MCP tools generate outputs that mathematically match the data served by the frontend API routes.
- **Approach**: The tests/test_mcp_data_parity.py suite executes priority MCP tools (e.g., simulate_budget_shift, get_budget_pacing) utilising FastAPIs TestClient to simultaneously fetch the raw UI data points.
- **Coverage**: It mathematically asserts that the backend tools (e.g., spend and pipeline logic) match the frontend source-of-truth exactly. This completely eliminates data divergence and forces strict alignment on cross-campaign scoping (using timeframe and campaign_id).

### 4. LLM-as-a-judge evaluation matrix & iterative refinement (Qualitative)
Deterministic unit tests only verify that Python code executes without crashing and that mathematical assertions hold true. They cannot evaluate whether an analytical payload is actually useful for strategic decision-making. For instance, an attribution query returning an unhandled dictionary or a multi-million-percent ROI multiplier is technically valid Python, but catastrophic for an executive relying on the AI copilot.

To solve this, I built an automated evaluation harness (scripts/ai_evals_matrix.py) that systematically tests all 16 analytical MCP tools across 30-day and 90-day timeframes, passing the raw JSON outputs to an independent Gemini LLM "Judge." The Judge scores each payload from 1 to 5 across three core dimensions:
- **Actionability:** Does the output contain concrete financial thresholds, verdicts, or directional recommendations that allow an executive to make a decision immediately?
- **Contextual Relevance:** Does the payload strictly answer the query intent without introducing noise, unrequested metadata, or raw database artifacts?
- **Sparsity:** Is the payload concise enough to fit into the LLM context window without diluting token attention?

#### Case study: Iterative hardening from v1 to v12
Running this harness revealed significant blind spots in the initial tool implementations. Over 12 iterations (tracked in tests/eval_reports/), I used the judge's qualitative feedback to systematically refactor app/services/analytics.py. 

The table below contrasts the baseline findings (ai_evals_report_v1.md) against the hardened state (ai_evals_report_v12.md):

| Tool function | v1 Actionability | v12 Actionability | Improvement details |
|---|:---:|:---:|---|
| simulate_budget_shift | **1 / 5** | **5 / 5** | Fixed linear extrapolation that projected an absurd pipeline values. Added an 18.5% audience fatigue dampener and safe fallbacks for zero-pipeline edge cases. |
| get_budget_pacing | **2 / 5** | **5 / 5** | Replaced a contradictory "On track" status (which masked budget shortfalls) with exact calculated daily spend targets.
| evaluate_trickle_threshold | **3 / 5** | **5 / 5** | Added explicit mathematical decay thresholds (comparing peak vs. 7-day traffic) and clear directives. |
| map_buying_committee | **1 / 5** | **5 / 5** | Enriched output to group personas by seniority and functional tier, explicitly flagging gaps (e.g., zero C-Suite touchpoints). |
| generate_ab_test_variants | **1 / 5** | **5 / 5** | Implemented recursive secondary LLM generation providing production-ready copy variants tailored to distinct buyer personas (CFO vs. CSO). |
| draft_outreach_sequence | **2 / 5** | **4 / 5** | Eliminated raw metadata leaking into email copy. Replaced with cleanly structured multi-step email and LinkedIn sequences. |
| get_intent_surge_signals | **1 / 5** | **4 / 5** | Fixed missing argument exceptions (account_identifier). Added velocity surges per account with 48-hour spike detection. |
| get_user_journey | **1 / 5** | **4 / 5** | Structured chronological multi-channel touchpoints with recommended follow-up windows. |
| **Suite benchmark** | **~2.1 / 5** | **~4.2 / 5** | **Crash rate reduced from 38% (6 of 16 tools failed) to 0%. Overall actionability doubled.** |

This quantitative improvement proves the value of the evaluation harness: instead of guessing what context the LLM needed, the continuous feedback loop exposed broken parameters, unhandled edge cases, and misleading business calculations before they could reach the presentation layer.

### 5. LLM resilience & cascading fallback testing
Because LLMs and remote inference APIs are subject to both non-deterministic response structures and burst-quota throttling, the backend incorporates comprehensive resilience testing:
- **Parser & Schema Failure Resilience**: The **tests/test_llm_parsers.py** suite uses **unittest.mock.patch** to inject synthetic, malformed JSON payloads. It asserts that when an LLM returns unparseable or truncated JSON, the backend catches the error cleanly and devolves to a safe fallback state rather than crashing the route with an HTTP 500.
- **Cascading Fallback & Quota Resilience**: The **tests/test_model_fallback.py** suite simulates HTTP 429 (**RESOURCE_EXHAUSTED**) quota limits on the primary **gemini-3.8-flash** model. It verifies that **generate_content_with_fallback** correctly quarantines exhausted API keys into the penalty box and cascades execution down the Flash model chain (**gemini-3.8-flash** $\rightarrow$ **gemini-3.6-flash** $\rightarrow$ **gemini-3.5-flash**), guaranteeing service continuity without user-visible failures.

### 6. Presentation layer testing (API routes)
Because the frontend relies on HTMX for dynamic swapping, the FastAPI backend acts as the presentation layer.
- **Approach**: The tests/test_api.py suite utilises fastapi.testclient.TestClient to programmatically fire HTTP GET requests against the core endpoints (e.g., /api/dashboard/overview).
- **Coverage**: It asserts that the HTMX endpoints correctly return 200 OK status codes and valid HTML fragments, ensuring the UI remains intact even as the underlying analytics engine is refactored.

### 7. Continuous integration (GitHub Actions)
To enforce quality control and prevent broken code from reaching production, the entire testing suite is automated via CI/CD.
- **Approach**: A GitHub Actions workflow (.github/workflows/ci.yml) is triggered on every push and pull request to the main branch. It provisions a clean environment, installs dependencies, and executes the full pytest suite.
- **Deployment gate**: The Render deployment pipeline is configured to monitor the GitHub commit status. If any test fails (e.g., an MCP contract mismatch), Render blocks the deployment, ensuring the live dashboard remains stable.

## 10. Caching, configuration and performance optimisation

To support scaling beyond the capstone prototype, the application manages configuration and caching with two distinct strategies.

### 1. Environment variable configuration
To decouple the application from its local environment and facilitate automated testing and deployment (e.g., on Render), core infrastructure paths are managed dynamically via environment variables (e.g., DATABASE_URL, REDIS_URL). This prevents hardcoded "magic strings" and allows the application to instantly pivot between development, testing, and production databases.

### 2. AI response caching (LLM layer)
To optimise latency and eliminate redundant LLM API costs, the application implements a two-tier caching strategy.  
- **Strategy**: The application utilises a centralised **Redis** instance to cache LLM responses. Before making an external API call to Gemini/OpenAI, the MCP layer hashes the deterministic context_str. If that exact data footprint was analysed recently, the system instantly returns the cached Markdown response from Redis. This prevents redundant API token expenditure and reduces UI latency.
- **Fallback mechanism**: To ensure absolute resilience, the system implements a graceful fallback. If the Redis server is unreachable, it automatically devolves to a local JSON persistent cache (llm_cache.json).

### 3. HTMX fragment caching & async offloading
Since the architecture relies heavily on server-side rendering (SSR) via FastAPI and Jinja2, the server bears the load of generating HTML strings.
- **Strategy**: FastAPI and Starlette's threadpool isolate blocking operations (such as SQLite aggregation queries and synchronous Gemini LLM API calls) onto separate worker threads. Furthermore, components that rely on the LLM (like the Strategic TL;DR and recommended AI actions) are lazily loaded using HTMX. This ensures the primary dashboard data renders instantly, providing the user with immediate access while the AI finishes processing in the background.

## 11. Technical debt & future architectural roadmap

While some deliberate architectural shortcuts were taken in the data access layer to prioritise milestone delivery, the following structural refactorings address technical debt and chart the roadmap for a production-grade version:

### 1. Multi-tier architectural decoupling: Domain, presentation, and data access (Roadmap)
The monolyth analytics.py ouples three distinct architectural tiers that represent key technical debt to address:
- **Descriptive telemetry vs. prescriptive actions:** Passive metric aggregations currently share a namespace with rule-based decision engines (e.g., asset fatigue decay alerts, next-best-action scoring, and sales target prioritization). Separating descriptive telemetry from prescriptive alert actions into a dedicated recommendation/action engine will allow business rules to evolve without risking core analytical regression.
- **Abstracting data access (repository pattern):** Both the UI services and MCP tools still manage ad-hoc SQL strings and connections internally. Introducing a formal repository.py layer will isolate raw database access behind entity repositories, converting the analytics and MCP modules into pure calculation and orchestration engines.

### 2. Full rollout of dependency injection
While FastAPI's native **dependency injection** (Depends(get_db)) has been successfully implemented in the UI routing layer (dashboard.py) to manage database connection lifecycles via the Unit of Work pattern, the core MCP AI tools in app/services/mcp_tools/ currently manage their own internal connections.
- **Roadmap action:** A future refactor will decouple the AI tool schema definitions from the underlying Python functions. This will allow me to inject database dependencies cleanly into the analytics layer without accidentally exposing the db connection parameter to the LLM's automated function calling schema.

### 3. Declarative tool chaining engine (MCP orchestration)
To fully eliminate the need for hardcoded late binding in complex agentic workflows, the system will eventually adopt a full **declarative tool chaining** engine. Instead of the LLM guessing parameters or using hardcoded string enums, the LLM will construct a directed acyclic graph (DAG) using JSON references (e.g., budget: "$ref.get_budget_pacing.shortfall"). This will require building a robust Python orchestration layer capable of parsing the LLM's graph, executing tools sequentially, mapping dynamic output variables to inputs, and handling execution failures gracefully.


## 12. Project retrospective: Answering the executive question

Returning to the problem posed at the beginning of this document: *Did spending $150,000 on the 'Offshore Wind' campaign help win the $10M Equinor contract?*

Under traditional fragmented analytics, answering that required manual data extraction across disconnected platforms, usually resulting in unhelpful vanity metrics. The Campaign Telemetry Engine solves this by uniting three core mechanisms:
1. **Deterministic identity resolution:** Programmatically tying top-of-funnel anonymous ad clicks to downstream CRM accounts and opportunity stages across an 18-month buyer journey.
2. **Constrained MCP orchestration:** Offloading financial math and multi-touch attribution to strictly verified Python functions, completely eliminating LLM calculation hallucinations.
3. **Action-driven server UI:** Surfacing asset fatigue and budget pacing anomalies automatically through HTMX, allowing marketing and sales teams to act on telemetry rather than just observing it.

By combining deterministic backend calculations with agentic synthesis, the engine allows the CMO to demonstrate verified multi-touch influence on the Equinor deal within seconds—bridging the gap between marketing spend and closed pipeline revenue.
