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
        INSERT INTO crm_users (user_id, first_name, last_name, company_name, industry, job_title, seniority, email, phone) 
        VALUES (1, 'Test', 'User', 'Acme Corp', 'Energy', 'CEO', 'C-Level', 'test@acme.com', '123');
        
        INSERT INTO crm_opps (opp_id, user_id, utm_campaign, pipeline_stage, pipeline_value, event_type, timestamp)
        VALUES ('OPP1', 1, 'CMP_TEST', 'Negotiation', 500000.0, 'Opportunity Created', datetime('now', '-5 days'));
        
        INSERT INTO crm_opps (opp_id, user_id, utm_campaign, pipeline_stage, pipeline_value, event_type, timestamp)
        VALUES ('OPP2', 1, 'CMP_TEST', 'Closed Won', 250000.0, 'Closed Won', datetime('now', '-2 days'));
        
        INSERT INTO ga4_events (event_id, cookie_id, user_id, event_name, page_viewed, session_id, utm_campaign, utm_source, utm_medium, timestamp)
        VALUES ('EV1', 'C1', 1, 'page_view', '/whitepaper', 'S1', 'CMP_TEST', 'linkedin', 'cpc', datetime('now', '-10 days'));
        
        INSERT INTO media_spend (spend_id, campaign_id, channel, spend_amount, impressions, clicks, date)
        VALUES ('SP1', 'CMP_TEST', 'LinkedIn', 10000.0, 50000, 500, datetime('now', '-10 days'));
    ''')
    conn.commit()
    conn.close()
    
    yield
    
    # Cleanup after tests
    os.close(db_fd)
    os.unlink(db_path)
