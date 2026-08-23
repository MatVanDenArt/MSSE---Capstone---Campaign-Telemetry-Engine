# Optimal B2B Telemetry Functionality Outline (Comparator)

This document serves as the "North Star" or ideal state of the application. It breaks down the system by the three core sections, aligning them with the target personas identified in the design document. It evaluates what static data should be shown, what mathematical anomalies should trigger the Action Center, and exactly what the AI Copilot should be able to execute.

---

## Section 1: The CMO Lobby (Strategic Overview)
**Target User:** CMO / VP of Marketing  
**Core Goal:** High-level strategic clarity, budget allocation, and board-ready ROI.

### 1. Static Content (The "What")
- **Campaign Pipeline & ROI:** The total pipeline revenue generated exclusively by this specific campaign, and the overarching cost to generate a Sales Qualified Opportunity (SQO).
- **Target Account Penetration:** What percentage of the Tier 1 accounts *assigned to this specific campaign* are actively engaging with its assets.
- **Velocity Impact:** How this specific campaign is accelerating the sales cycle (e.g., "Accounts exposed to this campaign close 2 months faster").
- **Topic Share of Voice (SOV):** How well this specific campaign is capturing digital dominance for its core theme (e.g., "Digital Twin") compared to primary competitors.

### 2. Action Center Triggers (The "So What")
*These are mathematical anomalies that the system detects automatically.*
- 🚨 **Campaign Underperformance:** "Pipeline generation for this campaign dropped 15% below its quarterly target."
  ➔ *Action: [Launch Budget Reallocation Simulator]*
- ⚠️ **Account Penetration Stagnation:** "No net-new Tier 1 accounts have engaged with this campaign in the last 30 days."
  ➔ *Action: [Analyze funnel bottlenecks & suggest top-of-funnel fixes]*
- 🚨 **Topic Threat Detected:** "Competitor 'Aker Solutions' has overtaken our Share of Voice for the core keywords targeted by this campaign."
  ➔ *Action: [Draft aggressive media buy strategy for Q4]*
- 🟢 **High-Efficiency Campaign:** "This campaign is generating pipeline at 50% of the target CPA. Consider scaling overall budget."
  ➔ *Action: [Draft budget increase request for VP Finance]*
- 🟢 **Regional Breakout:** "Engagement from APAC region Tier 1 accounts in this campaign surged by 40%."
  ➔ *Action: [Run correlation analysis to identify the winning regional assets]*

### 3. Copilot Capabilities (The "Now What")
**MCP Functions Required:** `get_executive_pipeline_kpis()`, `get_budget_pacing()`, `run_attribution_model()`
**Suggested Actions (1-click AI prompts):**
- *"Run a cross-campaign attribution analysis to determine which channel (LinkedIn vs Email) is generating the highest Pipeline ROI this quarter."*
- *"Forecast the Q4 Pipeline shortfall based on current MQL velocity and recommend precise budget reallocations to close the gap."*
- *"Identify the top 3 most cost-efficient buyer journeys that led to closed-won deals in the last 6 months, and suggest how to replicate them."*

---

## Section 2: Omnichannel Asset Performance
**Target User:** Campaign & Demand Gen Managers  
**Core Goal:** Tactical agility, maximizing asset lifecycle, and minimizing wasted ad spend.

### 1. Static Content (The "What")
- **High-Density Technical Matrix:** A scannable matrix of active, high-value assets (e.g., Decarbonization Whitepapers, ESG Reports, Digital Twin Webinars).
- **High-Value Account (HVA) Engagement Rate:** Instead of generic "traffic," it shows what percentage of viewers actually belong to Target Accounts (e.g., Shell, BP).
- **Firmographic Distribution:** Visual breakdown of which specific industries (e.g., Renewables vs. O&G) and job titles (Engineering vs. Procurement) are consuming the asset.
- **Health Status & Sparklines:** Left-border color coding based on performance vs. baseline, with 30-day rolling trendlines for targeted engagement.

### 2. Action Center Triggers (The "So What")
- 🚨 **Asset Fatigue:** "Traffic for 'Decarbonization Whitepaper' dropped > 50% from its 30-day peak."
  ➔ *Action: [Generate creative refresh brief for design team]*
- ⚠️ **High Bounce Rate:** "High traffic on 'Wind Energy LP' but conversion rate is < 1%."
  ➔ *Action: [Generate 3 A/B test variations for headline/copy]*
- 🚨 **Cost Inefficiency:** "CPA for 'Digital Twin Webinar' is double the campaign baseline."
  ➔ *Action: [Analyze channel mix & suggest budget reallocations]*
- 🟢 **Conversion Spike:** "The 'Digital Twin Webinar' just hit a 15% conversion rate, significantly outperforming the 5% baseline."
  ➔ *Action: [Identify lookalike audiences to scale ad spend]*
- 🟢 **Organic Viral Asset:** "Traffic for 'Decarbonization Whitepaper' surged 200% via organic search in the last 48 hours."
  ➔ *Action: [Automatically boost asset via Paid Social]*

### 3. Copilot Capabilities (The "Now What")
**MCP Functions Required:** `get_asset_impact_matrix()`, `evaluate_trickle_threshold()`, `compare_asset_baselines()`
**Suggested Actions (1-click AI prompts):**
- *"Analyze the fatigue rate of this whitepaper against our historical baseline and predict exactly when the CPA will exceed our acceptable threshold."*
- *"Identify the specific audience segments (e.g., by seniority or industry) that are bouncing from this landing page and suggest targeted messaging pivots."*
- *"Compare this underperforming webinar's engagement metrics to our top 3 historical webinars to isolate the failing variable (e.g., promotional channel vs. content)."*

---

## Section 3: Audience & Target Accounts (ABM)
**Target User:** Enterprise Sales Leadership  
**Core Goal:** Timing outbound outreach, bridging the marketing-sales divide, and closing deals.

### 1. Static Content (The "What")
- **Ranked Target Accounts:** A list of target companies (e.g., Shell, Equinor) sorted by an aggregate "Intent Score".
- **Buying Committee Map:** Visual tracker of known CRM contacts, explicitly segmenting technical stakeholders (e.g., HSE Directors, Lead Engineers) from commercial stakeholders (Procurement, VP Finance).
- **Intent Topic Clusters:** Word clouds or tags showing the specific technical themes the account is researching (e.g., "Carbon Capture," "Hydrogen," "Asset Decommissioning").
- **Journey Flow:** A visual Sankey diagram showing the 18-month cross-channel timeline of touches for that specific account.

### 2. Action Center Triggers (The "So What")
- 🟢 **Surging Intent:** "Multiple stakeholders from 'Equinor' engaged with bottom-funnel assets in the last 48h."
  ➔ *Action: [Draft personalized cross-channel outreach sequence for AE]*
- ⚠️ **Stalled Account:** "High early engagement from 'Shell', but zero activity in 14 days."
  ➔ *Action: [Suggest highly targeted 'Trigger Event' content to re-engage]*
- 🟢 **VIP Engagement:** "A new VP-level contact from a Target Account just downloaded the pricing calculator."
  ➔ *Action: [Alert Account Owner via Slack with 3-bullet prep summary]*
- 🟢 **Cross-Department Expansion:** "Marketing and Engineering personas at 'Wood Group' are now simultaneously consuming content."
  ➔ *Action: [Generate cross-functional executive summary for upcoming sales call]*

### 3. Copilot Capabilities (The "Now What")
**MCP Functions Required:** `get_account_penetration()`, `get_user_journey()`, `map_buying_committee()`
**Suggested Actions (1-click AI prompts):**
- *"Map the entire buying committee for 'Equinor', identify which key decision-makers have NOT engaged with our content, and draft targeted outreach to cover those blind spots."*
- *"Analyze the 6-month cross-channel journey for this stalled account and identify the exact touchpoint or time period where momentum dropped off."*
- *"Based on the highly specific technical assets consumed by the VP of Engineering, generate a contextual 'Trigger Event' email sequence for the Account Executive to deploy today."*

---

## Section 4: Temporal Reasoning & Timeframe Handling
Handling the "time element" (e.g., when a user asks about "last quarter") is a common stumbling block in AI data agents. To prevent hallucinations and maintain a frictionless UX, an optimal system utilizes a hybrid approach to temporal context:

### 1. Hidden Payloads (The Action Center Approach)
For 1-click "Suggested Actions" triggered by the Action Center, the system does not rely on natural language ambiguity. 
- **The Logic:** Because the backend already executed the math to detect the anomaly (e.g., a 7-day traffic drop), the exact start and end timestamps are baked into the HTML button as hidden data attributes (e.g., `data-start="2026-08-14"`). 
- **The Result:** When the user clicks the prompt, the backend executes the MCP function using exact, deterministic timeframes, bypassing language parsing entirely.

### 2. Global UI State Injection (The Pragmatic Fallback)
When users type open-ended questions into the chat box, forcing them to use specific date formats creates friction.
- **The Logic:** The dashboard features a global Date Picker (e.g., "Last 30 Days"). When the user sends a chat message, the HTMX request silently intercepts the state of this Date Picker and passes it to the backend.
- **The Result:** The LLM's system prompt is injected with context (e.g., *"The user is currently viewing data from [Start Date] to [End Date]. Scope all analysis to this timeframe unless explicitly instructed otherwise"*). This guarantees the AI's analysis aligns perfectly with the visual charts the user is looking at.

---

## Section 5: Trigger State Management & Simulation UX
An Action Center is only as effective as its state management. Without rigid logic, it devolves from a helpful Co-pilot into a noisy alarm system. The optimal state management rules are as follows:

### 1. Asynchronous Generation
Anomalies are **not** calculated on page load (which would drastically degrade UI performance). Instead, background CRON jobs run asynchronously (e.g., hourly or following a nightly ETL sync) to calculate standard deviations across thousands of assets. Detected anomalies are written to a lightweight `action_triggers` database table, which the UI queries instantly upon user login.

### 2. Time-To-Live (TTL) Ephemerality
Action triggers must be heavily time-bound based on data validity.
- **Urgent Triggers:** A 🟢 "Surging Intent" trigger is only valuable in the moment. It carries a TTL of 48 hours, after which it automatically expires.
- **Trend Triggers:** A 🚨 "Asset Fatigue" trigger may have a 7-day TTL. If the mathematical anomaly resolves itself organically (e.g., traffic randomly spikes again) before the user interacts with it, the background job automatically deletes the trigger to maintain inbox hygiene.

### 3. The "Inbox Zero" Philosophy
Once a user clicks a trigger's Action button (or explicitly clicks "Dismiss"), the database record is updated to `resolved: True`. The frontend immediately and optimistically removes the card from the Action Center feed via a smooth UI transition, preventing cognitive overload.

### 4. Simulating Execution (Capstone Strategy)
In a true enterprise environment, the Copilot executes actions via API integrations (e.g., sending a POST request to LinkedIn to pause a campaign). Because this Capstone is a simulation without access to live external APIs, execution is modeled via the Copilot Chat UI:
- **The Flow:** When a user clicks an Action Center button, the Copilot sidebar opens automatically.
- **The Latency:** The system introduces an artificial 1.5-second processing delay (complete with a loading spinner) to mimic actual API latency.
- **The Output:** The Copilot outputs a simulated confirmation. For text-generation actions (e.g., *Draft a creative brief*), it outputs the actual generated Markdown. For systemic actions (e.g., *Pause campaign*), it outputs a deterministic confirmation: *"Simulation: System authorized. Sent POST request to mock-LinkedIn-API. Campaign paused."* The trigger card is then removed from the feed.

---

## Appendix: Comprehensive MCP Function Library (The AI Toolbelt)
To function as a truly autonomous agent, the Copilot must have access to a broad "toolbelt" of deterministic functions it can chain together to solve complex user queries.

### 1. Analytics & Financial Operations
- `get_executive_pipeline_kpis(timeframe)`: Returns top-level ROI, Pipeline CPA, and Pipeline velocity.
- `get_budget_pacing(channel, campaign_id)`: Returns real-time burn rate vs. allocated budget.
- `run_attribution_model(model_type, timeframe)`: Re-calculates pipeline credit using W-Shaped, Linear, or First-Touch modeling on the fly.
- `simulate_budget_reallocation(source_channel, target_channel, amount)`: A predictive math model that forecasts pipeline impact if money is moved between channels.

### 2. Asset & Campaign Execution
- `get_asset_impact_matrix(campaign_id)`: Returns the core performance matrix (traffic, conversions, health).
- `evaluate_trickle_threshold(asset_id)`: Mathematical decay function predicting exactly when an asset will hit fatigue.
- `compare_asset_baselines(asset_a, asset_b)`: Isolates failing variables between two pieces of content by comparing cross-channel metrics.
- `generate_ab_test_variants(asset_id, variable)`: Text-generation function to output new headlines or copy based on historical conversion winners.

### 3. ABM & Sales Enablement
- `get_account_penetration(account_id)`: Returns the coverage percentage of a buying committee (e.g., "3 of 5 C-Suite engaged").
- `map_buying_committee(account_id)`: Identifies specific persona "blind spots" (e.g., "We have the CEO, but not the CTO").
- `get_intent_surge_signals(account_id)`: Flags sudden spikes in activity from specific target accounts over a 48-hour period.
- `get_user_journey(user_id)`: Returns the chronological, cross-channel touchpoints of a specific lead.
- `draft_outreach_sequence(persona, context_data)`: Generates personalized sales emails based strictly on the exact assets the persona consumed.
