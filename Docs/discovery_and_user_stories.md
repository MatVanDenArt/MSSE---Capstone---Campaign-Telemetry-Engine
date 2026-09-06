# Campaign Telemetry Engine: Discovery & User Stories

This document outlines the core personas, their goals, frustrations, and the specific user stories they require. It also maps these stories across the application's user journey to demonstrate how the Campaign Telemetry Engine solves their problems.

---

## Part 1: Persona Definitions & User Stories

### Persona 1: Sarah, The Chief Marketing Officer (CMO)
**Role:** Executive Leadership
**Goals:** Prove marketing ROI to the CEO/Board, ensure global budget pacing is on track, and understand the blended Cost-Per-Acquisition (CPA) across all channels.
**Frustrations:** Suffers from "dashboard blindness." Teams report on tactical vanity metrics (clicks, impressions) when she only wants to know if the campaign is actually generating sales pipeline. Has to wait weeks for data analysts to stitch cross-channel reports together.
**Scenario:** Sarah is preparing for a Monday morning board meeting. She needs an instant, reliable summary of whether the massive budget invested in the "Offshore Wind" campaign is actually converting into real business.

**User Stories (Executive Layer):**
1. **US-1.1:** As a CMO, I want to select a specific campaign from a global Lobby view, so I can instantly isolate performance data for that initiative.
2. **US-1.2:** As a CMO, I want an AI-generated Strategic TL;DR upon opening the dashboard, so I can immediately understand pipeline health without interpreting charts.
3. **US-1.3:** As a CMO, I want to see high-level KPI benchmarks (Spend, Accounts, CPA) compared to the previous timeframe, so I know if our marketing efficiency is trending up or down.
4. **US-1.4:** As a CMO, I want to view a top-level Share of Voice (SOV) metric, so I can see how our campaign is performing against core competitors.
5. **US-1.5:** As a CMO, I want to see Total Addressable Market (TAM) penetration, so I understand how much of our target market we have successfully engaged.
6. **US-1.6:** As a CMO, I want to ask the Copilot for a "Pipeline Velocity" calculation, so I can report to the board on how fast deals are moving through the funnel.

---

### Persona 2: Marcus, The Demand Gen Manager
**Role:** Tactical Campaign Execution
**Goals:** Optimize daily ad spend, rotate fatiguing assets before they drop in ROI, and understand which specific channels are driving the highest quality traffic.
**Frustrations:** Constantly logs into disjointed platforms (LinkedIn, GA4, Mailchimp). Often discovers wasted budget weeks after an ad stops performing. Doesn't have time to manually calculate rolling averages for every single asset.
**Scenario:** Marcus is doing his daily morning check-in. He needs to know if any active LinkedIn ads or Web landing pages are burning budget and need to be paused today.

**User Stories (Tactical Layer):**
1. **US-2.1:** As a Campaign Manager, I want to view an Omnichannel Asset Matrix, so I can see web, email, and social assets ranked in one unified view.
2. **US-2.2:** As a Campaign Manager, I want the system to mathematically flag "Asset Fatigue" automatically, so I don't have to manually hunt for dropping conversion rates.
3. **US-2.3:** As a Campaign Manager, I want to visualize multi-channel attribution (via Sankey or Funnel charts), so I can prove which initial touchpoints actually lead to pipeline.
4. **US-2.4:** As a Campaign Manager, I want to click an Action Center alert about an underperforming asset to open the Copilot, so I can get an immediate diagnosis of what went wrong.
5. **US-2.5:** As a Campaign Manager, I want the Copilot to recommend A/B test variations based on current asset telemetry, so I know exactly how to fix a failing ad.
6. **US-2.6:** As a Campaign Manager, I want the Copilot to simulate a budget shift (e.g., moving $10k from LinkedIn to Email), so I can predict the pipeline impact before making the change.

---

### Persona 3: Elena, The Enterprise Sales Director
**Role:** Revenue & Pipeline Generation
**Goals:** Prioritize high-intent accounts, map the buying committee, and draft highly contextualized outreach to close deals faster.
**Frustrations:** Marketing throws leads "over the fence" with no context. Sales reps don't know *what* the prospect read or watched, making initial outreach cold and generic.
**Scenario:** Elena is planning her team's weekly outreach strategy. She needs to know exactly which global accounts are surging in intent right now, and who specifically inside that company they should email.

**User Stories (Sales Alignment Layer):**
1. **US-3.1:** As a Sales Director, I want to view an Account Penetration list sorted by engagement score, so I know which companies my team should call first.
2. **US-3.2:** As a Sales Director, I want to click into a specific Target Account to see a chronological timeline of their engagement, so my reps have full context before pitching.
3. **US-3.3:** As a Sales Director, I want the Action Center to alert me of 48-hour "Intent Surges" on stalled accounts, so we can strike while their interest is peaked.
4. **US-3.4:** As a Sales Director, I want the Copilot to map the engaged "Buying Committee" within an account, so I can identify if we are missing key decision-makers (like the CTO).
5. **US-3.5:** As a Sales Director, I want the Copilot to automatically draft a highly personalized follow-up email based on the account's recent web activity, so my reps can act instantly.
6. **US-3.6:** As a Sales Director, I want the Copilot to summarize a specific user's multi-channel journey, so I know exactly what content resonated with them the most.

---

## Part 2: The User Journey Map (Screen by Screen)

### Step 1: The Lobby (Global Campaign Selection)
* **The Experience:** The entry point. The user selects the context of their work.
* **Stories Achieved:** 
  * US-1.1 (Select campaign to isolate data)
* **Copilot Integration:** The Copilot is on standby, establishing the global `campaign_id` context.

### Step 2: Executive Overview (The "What")
* **The Experience:** A high-level, board-ready dashboard. Heavily utilized by Sarah (CMO).
* **Stories Achieved:**
  * US-1.2 (Strategic TL;DR instantly loads via server-side cache)
  * US-1.3 (KPI Benchmarks & Sparklines)
  * US-1.4 (Share of Voice)
  * US-1.5 (TAM Penetration)
* **Copilot Integration (MCP Trigger):** Sarah clicks a button to *"Calculate Executive Pipeline KPIs"*. The MCP triggers the Python backend to crunch CPA anomalies, injecting deterministic math into the LLM to generate a board-ready summary.

### Step 3: Asset Performance (The "How")
* **The Experience:** High-density, tactical data view. Heavily utilized by Marcus (Campaign Manager).
* **Stories Achieved:**
  * US-2.1 (Omnichannel Asset Matrix)
  * US-2.3 (Funnel & Sankey Visualizations in UI Lab)
* **Copilot Integration (MCP Trigger):** Marcus selects *"Compare Asset Baselines"*. The MCP triggers Python to isolate performance gaps between Asset A and Asset B. The Copilot outputs a structured comparison, explaining *why* Asset A is winning.

### Step 4: Audience & Target Accounts (The "Who")
* **The Experience:** CRM alignment and account tracking. Heavily utilized by Elena (Sales Director).
* **Stories Achieved:**
  * US-3.1 (Account Penetration List)
  * US-3.2 (Chronological Timeline View)
* **Copilot Integration (MCP Trigger):** Elena clicks on "Shell Plc". She clicks *"Map Buying Committee"*. The MCP triggers the backend to filter CRM data for Shell, injecting the active roles (CTO, VP Eng) into the LLM. The Copilot identifies persona blind spots (e.g., "You have no engagement from Procurement").

### Step 5: The Action Center (The "So What")
* **The Experience:** Proactive system alerts surfacing mathematical anomalies. Used by Marcus and Elena.
* **Stories Achieved:**
  * US-2.2 (System flags Asset Fatigue)
  * US-3.3 (System flags 48-hour Intent Surges)

### Step 6: Copilot Recommended Actions (The "Now What")
* **The Experience:** The execution layer. The user resolves the alerts from the Action Center.
* **Stories Achieved:**
  * US-2.4 (Diagnose failing asset via Copilot)
  * US-2.5 (Generate A/B test variations)
  * US-2.6 (Simulate Budget Shift)
  * US-3.5 (Draft personalized sales outreach)
  * US-3.6 (Summarize user journey)
* **Copilot Integration (MCP Trigger - Deep Dive):** Elena clicks a "Surge" alert. She chooses the recommended action: *"Draft Outreach Sequence"*. The MCP triggers the `draft_outreach_sequence` Python function, pulling the exact whitepapers the account downloaded, and the LLM strictly formats a 3-step email sequence tailored perfectly to that telemetry.
