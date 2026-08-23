# Capstone V2: North Star Implementation Tasks

This document tracks the execution of the Endpoint Versioning (V2) architecture to implement the Optimal Comparator Outline without breaking the V1 MVP.

## Sprint 1: V2 Infrastructure & Data Augmentation
*Goal: Set up the V2 backend architecture and enhance the mock data generator.*
- [x] **Task 1.1:** Create `app/services/analytics_v2.py` as a carbon copy of the current file to begin isolated development.
- [x] **Task 1.2:** Update `schema.sql` to include the `action_triggers` table for Inbox Zero state management.
- [x] **Task 1.3:** Augment Python mock data generator to assign firmographic tags (Technical vs Commercial) to generated personas.
- [x] **Task 1.4:** Add `calculate_share_of_voice()` and `get_tam_penetration()` functions to `analytics_v2.py`.
- [x] **Task 1.5:** Implement backend application-level caching for analytics queries (Carried over from backlog).

## Sprint 2: V2 UI & AI Agent Integration
*Goal: Build the V2 visual components and wire the Copilot into the MCP Toolbelt.*
- [x] **Task 2.1:** Create `workspace_v2.html` and the corresponding `/api/v2/dashboard` routes.
- [x] **Task 2.2:** Add the "V1 vs V2" toggle switch to the main landing page.
- [x] **Task 2.3:** Map `analytics_v2.py` mathematical functions into `llm_rotator.py` via JSON schemas to enable Agentic execution.
- [x] **Task 2.4:** Update Copilot HTMX form to pass `activeTimeframe` state into the LLM system prompt.
- [x] **Task 2.5:** Redesign Action Center alert cards to embed 1-click execution buttons.
- [x] **Task 2.6:** Implement "Inbox Zero" HTMX endpoints (`hx-delete`) to resolve triggers in the DB.
- [x] **Task 2.7:** Implement Copilot Simulation UX (1.5s loading spinner -> artificial execution output).
- [x] **Task 2.8:** Build the CMO Lobby (Section 1) swapping generic metrics for TAM and SOV.
- [x] **Task 2.9:** Build the Target Accounts Modal featuring Sankey Timelines and Topic Word Clouds.
- [x] **Task 2.10:** Re-style all tables into clean, borderless list-views with micro-interactions.
