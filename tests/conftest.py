import os
import sqlite3
import pytest
import tempfile

# Set environment variable so analytics.py uses the test DB
db_fd, db_path = tempfile.mkstemp()
os.environ['DATABASE_URL'] = db_path

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # 1. Connect to the test db
    conn = sqlite3.connect(db_path)
    
    # 2. Read the schema we dumped
    schema_path = os.path.join(os.path.dirname(__file__), 'tests_schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = f.read()
    
    # 3. Execute the schema
    conn.executescript(schema)
    
    # 4. Insert some mock data for unit tests
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
    ''')
    conn.commit()
    conn.close()
    
    yield
    
    # Cleanup after tests
    os.close(db_fd)
    os.unlink(db_path)
