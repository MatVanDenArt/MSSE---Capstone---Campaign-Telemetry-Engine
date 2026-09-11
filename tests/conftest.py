"""
Global Pytest configuration and test fixtures.

Architectural purpose:
Provides session-scoped database isolation for the entire test suite.
Instead of running assertions against the live or simulated `capstone.db`,
this fixture provisions a temporary SQLite database initialized with `tests_schema.sql`
and pre-seeds deterministic baseline records for 'CMP_TEST'. This ensures:
  1. Complete isolation: Tests never mutate or depend on production file state.
  2. Speed: The lightweight schema executes and cleans up in milliseconds.
  3. Determinism: All analytical and parity tests run against known, predictable numbers.
"""

import os
import sqlite3
import pytest
import tempfile

# Point the application's database connection resolver to this temporary test file
db_fd, db_path = tempfile.mkstemp()
os.environ['DATABASE_URL'] = db_path

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Session-scoped fixture that builds the test database schema and seeds baseline records.
    # Automatically invoked for every test session and tears down the temp file upon completion.
    
    # 1. Establish initial SQLite connection to the temporary database file
    conn = sqlite3.connect(db_path)
    
    # 2. Execute the official relational schema definition
    schema_path = os.path.join(os.path.dirname(__file__), 'tests_schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = f.read()
    conn.executescript(schema)
    
    # 3. Insert deterministic seed records used across unit and data parity assertions:
    #    - 1 CRM user (CEO at Acme Corp)
    #    - 2 Opportunities: 1 Pipeline ($500k) + 1 Closed Won ($250k) = $750k total
    #    - 1 GA4 session on whitepaper asset
    #    - 1 LinkedIn media spend event ($10,000)
    conn.executescript('''
        INSERT INTO crm_users (user_id, account_id, company_name, email, first_name, last_name, job_title, seniority, persona_type) 
        VALUES (1, 100, 'Acme Corp', 'test@acme.com', 'Test', 'User', 'CEO', 'C-Level', 'Decision Maker');
        
        INSERT INTO crm_opps (event_id, user_id, account_id, event_type, pipeline_value, timestamp, utm_campaign)
        VALUES ('OPP1', 1, 100, 'Opportunity Created', 500000.0, datetime('now', '-5 days'), 'CMP_TEST');

        INSERT INTO crm_opps (event_id, user_id, account_id, event_type, pipeline_value, timestamp, utm_campaign)
        VALUES ('OPP2', 1, 100, 'Closed Won', 250000.0, datetime('now', '-2 days'), 'CMP_TEST');

        INSERT INTO ga4_events (session_id, cookie_id, utm_source, utm_campaign, page_viewed, bounce_flag, timestamp, user_id)
        VALUES ('S1', 'C1', 'linkedin', 'CMP_TEST', '/whitepaper', 0, datetime('now', '-10 days'), 1);

        INSERT INTO linkedin_events (event_id, campaign_id, ad_id, cookie_id, utm_source, spend_consumed, timestamp, user_id)
        VALUES ('EV1', 'CMP_TEST', 'AD1', 'C1', 'linkedin', 10000.0, datetime('now', '-10 days'), 1);

        INSERT INTO mailchimp_events (event_id, email, campaign_id, action, url_clicked, timestamp, user_id)
        VALUES ('MC1', 'test@acme.com', 'CMP_TEST', 'click', '/whitepaper', datetime('now', '-8 days'), 1);

        INSERT INTO content_metadata (url, title, asset_type, intent_topic)
        VALUES ('/whitepaper', 'Decarbonization Whitepaper', 'Whitepaper', 'Decarbonization');
    ''')
    conn.commit()
    conn.close()
    
    # Yield execution to the test runner
    yield
    
    # 4. Teardown: Safely close file descriptor and unlink temporary database file
    try:
        os.close(db_fd)
    except Exception:
        pass
    try:
        os.unlink(db_path)
    except Exception:
        pass

