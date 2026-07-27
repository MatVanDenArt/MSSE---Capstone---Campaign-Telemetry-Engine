User Stories: Wood Group Campaign Telemetry Engine
==================================================

1\. The Tactical View (The Digital Campaign Manager)
----------------------------------------------------

**User Story:**

> "As a Digital Campaign Manager, I want to see a unified view of LinkedIn ad spend, Mailchimp engagement, and GA4 website traffic for a specific active campaign, so that I can instantly understand our true blended Cost-Per-Account without manually downloading and VLOOKUP-ing three different CSV files."

*   **Architectural Insight / Edge Case Uncovered:**
    
    *   _The "Missing Touchpoint" Problem:_ What if a target account clicks a LinkedIn Ad and visits the website, but _never_ interacts with a Mailchimp email?
        
    *   _Action Required for Sprint 1:_ Our Python Pandas ETL script must use OUTER JOINs (or pd.merge(how='outer')) when combining the datasets. If we use strict inner joins, we will accidentally delete accounts that didn't interact across all three platforms, skewing our spend math.
        

2\. The Strategic View (The VP of Marketing)
--------------------------------------------

**User Story:**

> "As the VP of Marketing, I want the dashboard to provide a plain-English, one-paragraph AI narrative explaining _why_ a campaign is performing the way it is, so that I can confidently report to the executive board without having to interpret raw data tables myself."

*   **Architectural Insight / Edge Case Uncovered:**
    
    *   _The "Rambling AI" Problem:_ LLMs naturally want to talk too much. A VP does not want a 500-word essay.
        
    *   _Action Required for Sprint 2:_ Our system prompt to Gemini must include strict length guardrails (e.g., "Limit response to 3 sentences maximum. Use a professional, executive tone. Highlight the highest performing persona and the biggest drop-off point").
        

3\. The Sales Alignment View (The Account Executive)
----------------------------------------------------

**User Story:**

> "As a Sales Account Executive managing the 'Equinor' account, I want to use a dropdown to filter the campaign timeline specifically for Equinor, so that I can see exactly which whitepapers or emails the different members of their buying committee consumed before I make my sales call."

*   **Architectural Insight / Edge Case Uncovered:**
    
    *   _The "Content Blindspot" Problem:_ It is not enough for the timeline to just say "Asset Manager clicked email on Tuesday." The Account Executive needs to know _what_ they clicked to tailor their sales pitch.
        
    *   _Action Required for Sprint 1/3:_ We need to ensure our mock Mailchimp and GA4 data includes a utm\_content or page\_title column, and our HTMX timeline component must render that specific detail inside the visual node.
        

4\. The Analytical View (The Data Analyst / AI Chat)
----------------------------------------------------

**User Story:**

> "As a Marketing Analyst, I want to ask the chat interface 'What happens if we double our LinkedIn budget for this campaign next week?', so that I can mathematically justify budget reallocations to my boss."

*   **Architectural Insight / Edge Case Uncovered:**
    
    *   _The "Historical Baseline" Problem:_ To predict the future, the Python tool needs to know the exact conversion rate of the past.
        
    *   _Action Required for Sprint 3:_ The Python tool simulate\_budget\_shift must be programmed to query the SQLite database to calculate the _current_ Conversion-Rate-to-Pipeline before it applies the budget\_multiplier passed by the LLM.
        

5\. The Alerting View (The Regional Team Lead)
----------------------------------------------

**User Story:**

> "As a Regional Marketing Lead, I want a one-click button that pushes the AI-generated brief directly to our Microsoft Teams channel, so that I can alert the broader team about campaign momentum without copy-pasting formatting."

*   **Architectural Insight / Edge Case Uncovered:**
    
    *   _The "Ugly Formatting" Problem:_ MS Teams handles Markdown slightly differently than standard web browsers.
        
    *   _Action Required for Sprint 3:_ The Python webhook payload will need to format the JSON slightly to ensure line breaks and bold text render correctly in the Teams UI natively.
        

6\. The Account Penetration View (The ABM Lead)
-----------------------------------------------

**User Story:**

> "As an Account-Based Marketing (ABM) Lead, I want to see a summary table showing the total number of individuals engaged per target company (e.g., 30 from Shell, 15 from Aramco), broken down by their seniority level, so that I can verify if we are successfully reaching the actual buying committee (Directors/VPs) rather than just entry-level staff."

*   **Architectural Insight / Edge Case Uncovered:**
    
    *   _The "Messy Job Title" Problem:_ Raw data rarely says just "VP". You will get "Vice President", "V.P.", "Head of Dept", etc.
        
    *   _Action Required for Sprint 1/2:_ In our SQLite database and ETL process, we need a normalization function or an AI-mapping step that categorizes raw job titles into standardized seniority buckets (e.g., C-Suite, VP/Director, Manager, Individual Contributor) so the UI can group them cleanly.
        

7\. The Buyer Journey View (The Campaign Investigator)
------------------------------------------------------

**User Story:**

> "As a Campaign Investigator, I want to click on a specific company's aggregate metric and 'drill down' into an expanded, interactive timeline view, so that I can see the exact chronological sequence of touchpoints across all users from that company and understand what specific path led to a conversion."

*   **Architectural Insight / Edge Case Uncovered:**
    
    *   _The "UI Spiderweb / Data Avalanche" Problem:_ If 30 users from Shell interacted 15 times each over a month, trying to render 450 nodes on a single visual timeline will look like a messy spiderweb and potentially cause browser lag.
        
    *   _Action Required for Sprint 2/3:_ The frontend HTMX implementation for the "deep view" needs lazy-loading or pagination. Furthermore, the UI must include grouping toggles (e.g., "Group by User" or "Collapse by Week") so the user can digest the complex timeline without being overwhelmed by visual noise.