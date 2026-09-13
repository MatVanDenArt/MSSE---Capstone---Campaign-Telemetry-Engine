# Campaign telemetry engine: Design and architecture document

This document details the architectural decisions, design patterns, data simulation pipeline, and testing strategies implemented for the Campaign Telemetry Engine capstone project.

## 1. Project rationale: Solving the actionability gap in B2B marketing

### The problem: Fragmented telemetry and 18-month attribution cycles
Enterprise B2B marketing operates under fundamentally different constraints than B2C e-commerce:
- Sales cycles routinely span 12 to 18 months.
- Purchasing decisions involve multi-stakeholder buying committees (technical evaluators, commercial directors, and C-suite economic buyers) rather than individual impulse shoppers.
- Marketing touchpoints are fragmented across siloed channels: anonymous website browsing (Google Analytics 4), outbound nurture cadences (Mailchimp), sponsored ad campaigns (LinkedIn Ads), and sales opportunity tracking (Salesforce CRM).

In practice, this creates an attribution breakdown at the top of the funnel. A prospective buyer typically researches anonymously across several visits before submitting a form or accepting an email nurture sequence. When analytics systems evaluate these touchpoints in isolation, paid acquisition channels appear to generate zero pipeline, leaving marketing leadership unable to tie early-stage campaign investments to multi-million-dollar closed contracts.

### The operational bottleneck: From observation to action
Extracting actionable intelligence from this landscape historically required either dedicated data analysts writing complex ad-hoc SQL joins across data warehouses, or marketers manually stitching together spreadsheets from disconnected dashboards. Even when anomalies were identified—such as an ad asset exhausting its audience and burning budget—a significant lag separated observation from operational intervention.

### The engineering objective
The Campaign Telemetry Engine addresses these challenges through three core systems:
1. **Deterministic identity resolution:** A simulated ETL pipeline that stitches anonymous early-stage cookie IDs to downstream CRM profiles retroactively, establishing a continuous chronological timeline from first ad click to closed deal.
2. **Prescriptive analytics with constrained AI orchestration:** Offloading financial math, multi-touch attribution, and fatigue detection to deterministic, strictly typed Python functions (via an MCP-inspired tool interface), using the LLM solely to synthesize patterns into strategic executive recommendations.
3. **Action-driven server UI:** An HTMX and FastAPI interface that surfaces anomalies directly within an Action Center, enabling marketing and sales teams to review and trigger operational workflows with single-click actions.

## 2. System design and user interface architecture

The user interface follows three core functional modules designed for high information density and fast execution:

1. **Telemetry visualisations:** 
   Compact, scannable metric cards, multi-channel funnels, and performance tables present unified cross-channel data. Visual elements (color accents, sparklines, and status badges) are constrained to communicate channel performance and anomalies without visual clutter.
2. **The action centre:** 
   A dynamic queue of priority tasks surfaced by the analytics engine. The backend continuously evaluates live data against operational thresholds (e.g., flagging when an asset's 7-day traffic drops by more than 95% from its peak) and stages actionable intervention tasks.
3. **The AI copilot sidebar:** 
   An interactive conversational panel embedded directly alongside the dashboard. When an operator investigates a priority action, the copilot runs relevant backend diagnostic tools, summarizes the strategic context, and renders executable action buttons to trigger stack workflows (e.g., scheduling nurture sequences or syncing buying committee contacts to CRM).

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

The intelligence layer of the copilot is driven by Google's Gemini Flash model family, utilizing an automated fallback cascade across **gemini-3.6-flash**, **gemini-3.8-flash**, and **gemini-3.5-flash**. Choosing this model family and configuring this multi-tier architecture emerged from analyzing the actual demands of an agentic telemetry workflow against real-world API rate limits, latency profiles, and cost structures.

### Model landscape and practical trade-offs
Integrating an LLM into an analytical telemetry system requires evaluating real-world latency, cost, and rate limits rather than defaulting to the largest frontier model:

1. **Offloading computation to deterministic Python:** In this architecture, the LLM is prohibited from performing raw arithmetic, statistical aggregations, or SQL joins. All calculations (blended CPA, pacing run rates, multi-touch weightings) run deterministically in Python against indexed SQLite tables in sub-millisecond time. The model's responsibility is strictly synthesis: parsing verified JSON outputs and explaining business implications to a marketing operator. Paying the latency and cost penalty of a frontier reasoning model (e.g., Gemini Pro or GPT-4) to summarize pre-computed JSON is an inefficient use of resources.
2. **Interactive UI latency:** The copilot lives in a server-driven HTMX interface with real-time SSE streaming. Operators investigating asset fatigue expect near-instant feedback. Frontier models typically exhibit higher time-to-first-token (TTFT) and slower token generation, turning conversational workflows into an awkward waiting game. Flash-tier models routinely respond in under 800ms.
3. **Free-tier quota constraints:** For a capstone evaluation and demonstration on Render, relying on Google AI Studio's free tier was a practical design choice. On this tier, Pro models are restricted to 2 requests per minute and 50 requests per day. Because a single user interaction can trigger multi-turn diagnostic sequences (evaluating buying committees, checking fatigue, and drafting sequences), a Pro model would exhaust the daily quota after three or four queries. Flash models provide 15 RPM and 1,500 RPD, offering the necessary headroom for continuous test runs and live demonstrations.
4. **Local SLM limitations:** Sub-3B parameter local models (e.g., Gemma-2B, Llama-3.2-1B) struggle significantly with complex function-calling schemas. In early testing, smaller local models frequently hallucinated nonexistent parameters or failed to return valid JSON tool calls. Gemini Flash provides high tool-calling reliability while remaining within acceptable latency and cost boundaries.

### Model selection in practice: Defaulting to gemini-3.6-flash vs. 3.8-flash preference

From an analytical reasoning perspective, **gemini-3.8-flash** is technically the preferred model: it writes with a crisper commercial tone and demonstrates stronger nuance when synthesizing complex committee data.

However, continuous evaluation runs revealed an operational bottleneck: because 3.8-flash is Google's newest and most popular flash model, it suffers from heavy congestion on the shared free tier, causing frequent HTTP 429 (**RESOURCE_EXHAUSTED**) quota throttling and latency spikes.

To guarantee system stability during live evaluations and test automation, **gemini-3.6-flash** was selected as the default primary model due to its consistent availability on the free tier. When requests fail or hit rate limits, the fallback cascade automatically attempts 3.8-flash and 3.5-flash.

#### Model fallback cascade
- Primary model: **gemini-3.6-flash**
- Fallback model 1: **gemini-3.8-flash**
- Fallback model 2: **gemini-3.5-flash**

#### Practical advantages of 3.6-flash:
- **Consistent availability:** 3.6-flash experiences significantly less traffic on the free tier, providing reliable uptime and vastly fewer 429 rate-limit errors.
- **Reliable tool calling:** 3.6-flash parses and executes the 16 MCP tool declarations with high schema compliance, adhering strictly to required arguments without parameter hallucination.
- **Cascading resilience:** If 3.6-flash encounters an error, the rotating fallback chain attempts 3.8-flash and 3.5-flash across the API key rotation pool before raising an exception.

### AI service abstraction layer
All LLM interactions are isolated within **app/services/llm_rotator.py** rather than dispersed across route handlers.

This abstraction provides three practical benefits:
- **Centralized schema definitions**: Tool schemas are defined and updated in one place.
- **Provider agnosticism**: Application routes pass text prompts to the rotator, which handles provider SDK communication, credential rotation, and response caching.
- **Migration path**: Migrating to an alternative cloud provider or local LLM server requires changing only the adapter inside **llm_rotator.py**, leaving application routes untouched.

## 5. AI architecture: Model context protocol (MCP) tool integration

To prevent language model hallucinations when analyzing marketing telemetry, the AI copilot uses an architecture modeled after the Model Context Protocol (MCP):

- **Deterministic data anchoring**: The LLM never writes raw SQL queries or performs metric math. Instead, dedicated Python functions execute all data retrieval and calculations.
- **Structured tool calling**: The copilot provides the model with 16 structured JSON tool definitions (**mcp_tools**). When an analytical question or Action Center task is received, Gemini selects the appropriate tool and arguments. The FastAPI backend executes the corresponding Python function in **app/services/mcp_tools/** against the SQLite database, returning the verified JSON payload back to the model.
- **Grounding and consistency**: Because the LLM is restricted to interpreting and synthesizing verified data returned by deterministic functions, financial calculations, CPAs, and conversion counts remain mathematically consistent.

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

To support my project idea of a modern AI enabled marketing telemetry engine I chose a lightweight, server-driven architecture to prioritize development speed, to keep LLM orchestration and data processing in the same Python process.
Building a data-heavy telemetry engine with an embedded AI copilot presents an architectural tension: the application requires the analytical and agentic orchestration power of Python, yet demands the snappy, responsive feel of a modern SaaS dashboard. Rather than defaulting to a complex, decoupled architecture—such as a React frontend wired to a separate Python microservice, I deliberately chose a lightweight, server-driven stack built around FastAPI, HTMX, and SQLite. This combination eliminates the overhead of synchronising state across client and server, allows streaming AI responses and SQL query results to be handled natively in one place and ensures portability with minimal configuration overhead whether the project is running locally or is deployed to the cloud on Render.

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
The following section outlines the key structural patterns used in the codebase, the engineering rationale behind them, and intentional trade-offs made during development.

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

### Session isolation: Moving beyond global state

Early prototypes maintained **chat_history** and **active_chat_tasks** as module-level globals—a convenient shortcut for initial single-user development that created concurrency leaks in multi-user settings. I resolved this by refactoring **app/api/chat.py** to use cookie-authenticated session IDs (**cte_session**) backed by dual-tier persistence: Redis as primary (with 24h TTL) and local JSON files as dev fallback. Chat history and streaming tasks are now strictly isolated per user session.



## 8. Deployment strategy and hosting architecture

### Capstone demonstration: Render

**Live demo on Render** 
- https://msse-capstone-campaign-telemetry-engine.onrender.com/

For the capstone demonstration, I deployed the engine on **Render** (free tier) with **GitHub Actions**:
- **Zero-configuration setup:** The embedded SQLite database (**capstone.db**) is bundled directly into the container, allowing evaluators to access a fully working dashboard immediately without configuring external databases.
- **Native Redis:** A managed Redis instance handles session state and AI telemetry caching in a live cloud environment without local container overhead.
- **Automated CI/CD:** Every push to **main** triggers automated pytest suites in GitHub Actions that need to successfully pass before automatic deployment can take place.


### Production evaluation: Single company (~50 users)

If deployed internally at a single enterprise client with roughly 50 marketing managers and commercial leads, keeping the deployment infrastructure simple and cost efficient is the optimal approach. The optimal solution needs to allow the prototype to find its way into the hands of the users easily and without any friction. It must be cost efficient and demonstrate value without placing a heavy burden on the IT department to deploy and maintain the solution. Balancing cost, data privacy and security concerns are the main  factors to consider, across both hosting infrastructure and LLM model choice. 

#### 1. Hosting infrastructure options

| Option | Stack | Monthly Cost | Maintenance Effort | Practical Fit |
| :--- | :--- | :--- | :--- | :--- |
| **Option A: Render managed** | FastAPI Web Service + Managed PostgreSQL + Managed Redis | **~\$50–\$60/mo** | **Near zero.** Fully managed SSL, automated backups, and push-to-deploy. | **Best choice for speed and cost.** Low overhead, perfect for an internal team. |
| **Option B: AWS serverless / lightweight** | AWS App Runner + RDS PostgreSQL + ElastiCache | **~\$90–\$150/mo** | **Low.** Serverless containers; no EC2 instances or cluster management. | Fits directly inside corporate AWS tenant and IT security policies. |

#### 2. AI model strategy and data privacy

Because enterprise marketing telemetry involves commercially sensitive client and pipeline data, the AI backend must balance privacy guarantees against cost and reasoning power:

| Strategy | Architecture | Cost Structure | Privacy & Governance | Verdict for a single enterprise client |
| :--- | :--- | :--- | :--- | :--- |
| **Cloud API (Gemini / OpenAI)** | Direct API calls via **llm_rotator.py** with multi-tier fallback (3.6/3.8 Flash) | **~\$5–\$20/mo** (fractions of a cent per query; free-tier for light usage). Redis prompt caching reduces calls further. | Enterprise agreements offer zero-data-retention. | **Recommended baseline if company security allows third-party API exposure.** Highest reasoning capability, lowest cost, and zero maintenance. |
| **Enterprise private cloud (AWS Bedrock / Azure OpenAI)** | Managed private endpoints within the company’s corporate cloud account | **Pay-per-token** (~$20–$50/mo) with zero idle compute costs. | **High.** Data is legally and cryptographically isolated within the corporate tenancy. | **Best compromise if corporate security mandates zero third-party API exposure.** |
| **Self-hosted on-premises (Ollama / vLLM)** | Open-source model (e.g., Llama 3 8B) running on internal company hardware | **High initial CapEx (\$10k+)** for enterprise server/GPU hardware. \$0 token fees, but ongoing internal IT maintenance. | **Absolute.** Zero external data transmission. | Unnecessary cost and complexity for 50 users; weaker reasoning on complex tool calling. |

Thanks to the adapter pattern in **app/services/llm_rotator.py**, switching from public Gemini APIs to a corporate private endpoint (or local LLM) requires changing only the **OPENAI_BASE_URL** environment variable, without touching application logic.

#### 3. Authentication and access control for enterprise rollout
The capstone prototype intentionally runs without an authentication layer so that evaluators can access the live Render URL immediately without creating accounts or managing login tokens.

In an enterprise environment, the application would integrate directly with the company's existing identity provider such as Microsoft Entra ID or Okta. FastAPI handles this cleanly via session middleware or **JSON web token** validation at the entry proxy, ensuring that user identity and organizational groups are verified before requests ever touch the application routes.

### Recommended production path

For a single enterprise client with approximately 50 users, the most pragmatic path is **Render deployment with managed PostgreSQL database and Gemini cloud API** (under an enterprise zero-retention agreement). The entire platform cost would be around **$80/month total** with zero server maintenance. If corporate IT mandates keeping all workloads inside company cloud boundaries, the application deployment could pivot seamlessly to **AWS App Runner + AWS Bedrock** without requiring Kubernetes or dedicated infrastructure teams.

### When would a heavy cloud architecture make sense?

Complex orchestration (Kubernetes, Celery worker clusters, multi-region database failover) only becomes justified in the event that the application evolves from an internal tool into a commercial multi-tenant SaaS product serving dozens of external enterprises with high-throughput event ingestion. In the context of the prototype that is meant to represent a single enterprise client, keeping the deployment simple, managed, and inexpensive is an optimal solution.

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
- **Parser & schema failure resilience**: The **tests/test_llm_parsers.py** suite uses **unittest.mock.patch** to inject synthetic, malformed JSON payloads. It asserts that when an LLM returns unparseable or truncated JSON, the backend catches the error cleanly and devolves to a safe fallback state rather than crashing the route with an HTTP 500.
- **Cascading fallback & quota resilience**: The **tests/test_model_fallback.py** suite simulates HTTP 429 (**RESOURCE_EXHAUSTED**) quota limits on the primary **gemini-3.8-flash** model. It verifies that **generate_content_with_fallback** correctly quarantines exhausted API keys into the penalty box and cascades execution down the Flash model chain (**gemini-3.8-flash** $\rightarrow$ **gemini-3.6-flash** $\rightarrow$ **gemini-3.5-flash**), guaranteeing service continuity without user-visible failures.

### 6. Presentation layer & endpoint smoke testing (API routes)
Because the frontend relies on HTMX for dynamic swapping, the FastAPI backend acts as the presentation layer.
- **Approach**: The tests/test_api.py carries out smoke testing of core routes and verifies container readiness.
- **Coverage**: It asserts that UI endpoints (/api/dashboard/overview, /api/dashboard/performance, /api/dashboard/action-center) return 200 OK with valid HTML fragments, verifies live telemetry endpoints (/api/telemetry/ai-calls), and tests the /health container probe used by Render.


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

While deliberate architectural trade-offs were made to prioritize functional milestone delivery, the following areas represent identified technical debt and form the roadmap for a production-grade release:

### 1. Data access abstraction & complete dependency injection (Repository pattern)
Both the UI services and MCP tools currently manage ad-hoc SQL strings and direct SQLite connections internally (**get_db_connection()**). While FastAPI's native **Depends(get_db)** pattern is applied in the HTTP routing layer (**dashboard.py**), the MCP tool functions manage their own connections to prevent the **db** parameter from leaking into the LLM's function-calling JSON schema.

**Roadmap action:** 
Introducing a formal **repository.py** layer will decouple raw SQL execution from business logic. Entity repositories (e.g., **CampaignRepository**, **OpportunityRepository**) will accept injected database connections at the service layer, while outer tool wrappers expose clean parameter contracts to the LLM. This converts the MCP modules into pure calculation and orchestration engines without leaking internal database handles into prompt contexts.

### 2. Separation of descriptive telemetry from prescriptive alert logic
The monolithic **app/services/analytics.py** facade currently couples passive metric aggregations (e.g., CPA calculations, TAM percentages) with rule-based operational alert logic (e.g., asset fatigue thresholds, next-best-action scoring, and sales target prioritization). 

**Roadmap action:** 
Separating descriptive reporting queries from the prescriptive recommendation rules into an independent decision engine will allow marketing business logic to evolve without risking regressions in core analytical calculations.

### 3. Declarative tool chaining engine (MCP orchestration)
To eliminate the need for hardcoded string late-binding (e.g., **budget="REMAINING_BUDGET"**) in multi-step agentic workflows, the system will adopt a declarative tool-chaining engine. Instead of relying on string tokens, the LLM will output a directed acyclic graph using JSON references (e.g., **budget: "$ref.get_budget_pacing.shortfall"**). A dedicated Python orchestration runner will parse the graph, execute dependent tools in topological order, pass dynamic variables between stages, and handle partial tool failures gracefully.

### 4. Accessibility and inclusive UX (WCAG 2.1 compliance)
The current user interface prioritizes high-density data presentation and dark-mode aesthetic contrast tailored to rapid executive scanning. However, several accessibility (a11y) gaps remain that must be addressed for formal enterprise deployment:
- **Keyboard navigation & focus management:** While standard form controls are navigable, custom modal drawers (such as the target persona journey timeline and deep-dive account panels) lack formal keyboard focus traps and **Escape**-key dismissal handlers.
- **Screen reader semantics:** HTMX dynamic swaps (**hx-swap="innerHTML"**) update content without full page reloads. Adding **aria-live="polite"** regions to the AI copilot chat stream, status strips, and dynamically swapped metric tabs is necessary to ensure screen readers announce incoming streaming tokens and filter updates.
- **Color contrast & chart accessibility:** Certain low-saturation badge combinations require calibration against WCAG 2.1 AA standards. In addition, data-dense Chart.js canvas visualizations currently lack fallback tabular representations (**sr-only** tables) for visually impaired users.

### 5. Identity, role-based access, and tenant data isolation
Because the prototype was built to demonstrate attribution mechanics rather than user management, the current database schema assumes a single, open organization. While queries are scoped by campaign_id, there is no concept of user ownership or tenant separation.

**Roadmap action:**
- **Tenant isolation:** Moving to PostgreSQL in production will allow implementing row-level security or mandatory organization_id filters across all repository queries, ensuring one company's pipeline data can never leak into another tenant's session.
- **Role-based permissions:** Not every marketing user needs access to raw contract amounts or executive-tier CRM notes. Introducing roles (e.g., *Campaign Manager* vs. *Commercial Director*) will let the application filter which MCP tools the AI copilot is allowed to invoke for a given session.
- **Audit logging:** Enterprise compliance (GDPR) requires tracking what commercial data users query. Adding an audit log middleware to record prompt queries and tool execution arguments will provide the required audit trail.


## 12. Conclusion & retrospective

When I started this capstone, the goal was simple: take 18 months of messy, disconnected B2B touchpoints and turn them into an attribution model and AI copilot that people could actually trust.

Looking back at the build, two main lessons shaped the final architecture:

- **Calculations belong in code, not in prompts.** During early testing, letting the LLM do calculations or extrapolate numbers produced wild estimates and broken logic. The breakthrough came from running 12 rounds of evaluations using the judge harness and locking down all the numbers behind strict, unit-tested Python functions. Once the model was restricted to explaining verified calculations rather than inventing them, the copilot became dependable.
- **The unified stack is a strength, but with trade-offs.** Building the entire app around FastAPI, Jinja2, and HTMX allowed the data logic, UI rendering, and AI copilot to share a single source of truth in Python. This eliminated multi-tier setup challenges like the contract drift and API synchronization, and made it possible to test the whole data flow end-to-end. While a high-concurrency production deployment would eventually warrant separating the long-lived AI streaming workers from the presentation layer, keeping them unified in this prototype project kept the architecture clean, transparent, and focused on core data accuracy and actionability.

The campaign telemetry engine prototype delivers exactly what was needed: reliable attribution numbers that match across the UI and the AI copilot, paired with practical next steps marketing teams can take right away.
