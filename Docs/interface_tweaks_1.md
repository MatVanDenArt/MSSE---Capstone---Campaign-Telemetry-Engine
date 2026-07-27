## 1. Global Layout & The Campaign Lobby
**Goal:** Remove the burden of remembering campaign IDs. The user selects a context before seeing any data.

*   **Initial View (The Lobby):** A full-page, clean grid layout. 
*   **Filters:** Top of the screen includes simple toggle buttons: `[All]` `[🟢 Active]` `[⚪ Completed]`.
*   **Campaign Cards:** Render a grid of cards for each campaign. 
    *   *Visual Hierarchy:* Campaign Name (H2), Date Range, Status Badge (Green dot for Active, Gray for Completed).
    *   *Key Metric:* One prominent metric at the bottom of the card (e.g., "Live Pipeline: $1.2M").
*   **Interaction (htmx):** Clicking a card triggers an `hx-get` to the server, which swaps the entire screen to the "Workspace View" for that specific campaign.

---

## 2. The Workspace Shell (Split-Screen)
**Goal:** A side-by-side layout that separates conversation from heavy data visualization.

*   **Layout Structure:**
    *   **Top Bar:** A breadcrumb showing the current context (e.g., `🏠 Campaigns / 🟢 Offshore Wind Q3`).
    *   **Left Pane (30% width - Fixed):** The Chat Interface. Contains a vertically scrolling chat history and a sticky text input at the bottom.
    *   **Right Pane (70% width - Scrollable):** The "Canvas". When a campaign is loaded, this pane immediately populates with the **Standard Default Dashboard** (Features 3, 4, and 5 below).
*   **Interaction (htmx):** When the user types in the chat, it sends an `hx-post` to the FastAPI backend. The backend determines if it should append a chat bubble to the Left Pane, OR return a filtered/new HTML chart fragment targeting a specific `<div>` in the Right Pane.

---

## 3. Feature: Interactive Campaign Timeline & Velocity Mapper
**Goal:** Visually correlate outbound marketing releases with inbound engagement over an 18-month window.

*   **Placement:** The first module at the top of the Right Pane canvas.
*   **Visual Layout (Stacked Charts sharing an X-axis):**
    *   *Top Section (The Gantt):* A horizontal timeline. Show notable campaign releases (Webinars, Email Blasts, Tradeshows) as color-coded flags or milestone markers.
    *   *Bottom Section (The Velocity Line Graph):* Directly below the timeline, render a multi-line graph showing "Website Traffic" and "Form Submissions". 
*   **Insight Displayed:** Proves whether a specific asset release actually caused a spike in user engagement.
*   **Styling:** Use a clean, enterprise aesthetic with subtle gridlines. 

---

## 4. Feature: Account & Persona Matrix
**Goal:** Show pipeline *quality* by breaking down exactly who is engaging from target enterprise accounts.

*   **Placement:** The second module in the Right Pane canvas.
*   **Visual Layout (Data Grid / Heatmap):**
    *   *Rows:* Target Account Names (e.g., "Equinor", "BP", "Shell").
    *   *Columns:* Seniority Levels (C-Suite, VP/Director, Manager, Individual Contributor).
    *   *Cells:* Display a numeric "Engagement Score". 
    *   *Styling:* Apply CSS heatmap coloring to the cells (e.g., pale indigo for low engagement, deep indigo for high engagement).
*   **Insight Displayed:** Reveals if the campaign is reaching decision-makers or just entry-level researchers.
*   **Interaction:** Clicking a cell (e.g., the C-Suite cell for "BP") uses htmx to open a modal or slide-out tray revealing the names of the specific assets those individuals consumed.

---

## 5. Feature: Asset Fatigue & Conversion Monitor
**Goal:** Track the lifecycle and decay of specific content pieces to advise on budget allocation.

*   **Placement:** The third module in the Right Pane canvas.
*   **Visual Layout (Card Grid):**
    *   Render a grid of smaller cards, each representing one piece of content (e.g., "Q3 Whitepaper", "Technical Demo Video").
    *   *Card Anatomy:* Title, Format Badge, and a Status Badge (🟢 Healthy, 🟡 Saturated, 🔴 Action Required).
    *   *Trend Visual:* Include a small 30-day sparkline (mini line chart) showing the conversion rate trend. If the line is trending down sharply, the status should be Red.
*   **Insight Displayed:** Tells the marketer which content to heavily promote and which content to stop spending ad money on.

---

## 6. Feature: Next-Best-Action Alerts (Proactive Engine)
**Goal:** System-generated alerts for anomalies, allowing one-click corrective action.

*   **Visual Layout (Floating Toasts or Sticky Banner):**
    *   Render these as prominent notifications floating in the top right of the application, or as a sticky banner directly above the canvas.
    *   *Anatomy:* Icon (Severity), Insight Text (e.g., "⚠️ Traffic from the UK dropped 50%, but LinkedIn ad spend remains high."), and a primary Action Button.
*   **Interaction (htmx):** The Action Button (e.g., `[ Pause UK Ads ]`) should be wired with an `hx-post` to a specific FastAPI endpoint that executes the action and updates the button state to `[ Ads Paused ]` without reloading the page.