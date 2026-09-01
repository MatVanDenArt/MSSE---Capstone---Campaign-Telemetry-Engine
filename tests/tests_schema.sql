CREATE TABLE action_triggers (id TEXT PRIMARY KEY, campaign_id TEXT, type TEXT, message TEXT, action_payload TEXT, resolved_status BOOLEAN DEFAULT 0, created_at TIMESTAMP, expires_at TIMESTAMP);
CREATE TABLE "crm_users" (
"user_id" INTEGER,
  "account_id" INTEGER,
  "company_name" TEXT,
  "email" TEXT,
  "first_name" TEXT,
  "last_name" TEXT,
  "job_title" TEXT,
  "seniority" TEXT,
  "persona_type" TEXT
);
CREATE TABLE "crm_opps" (
"event_id" TEXT,
  "user_id" INTEGER,
  "account_id" INTEGER,
  "event_type" TEXT,
  "pipeline_value" REAL,
  "timestamp" TEXT,
  "utm_campaign" TEXT
);
CREATE TABLE "mailchimp_events" (
"event_id" TEXT,
  "email" TEXT,
  "campaign_id" TEXT,
  "action" TEXT,
  "url_clicked" TEXT,
  "timestamp" TIMESTAMP,
  "user_id" INTEGER
);
CREATE TABLE "linkedin_events" (
"event_id" TEXT,
  "campaign_id" TEXT,
  "ad_id" TEXT,
  "cookie_id" TEXT,
  "utm_source" TEXT,
  "spend_consumed" REAL,
  "timestamp" TIMESTAMP,
  "user_id" REAL
);
CREATE TABLE "ga4_events" (
"session_id" TEXT,
  "cookie_id" TEXT,
  "utm_source" TEXT,
  "utm_campaign" TEXT,
  "page_viewed" TEXT,
  "bounce_flag" INTEGER,
  "timestamp" TIMESTAMP,
  "user_id" REAL
);
CREATE TABLE "content_metadata" (
"url" TEXT,
  "title" TEXT,
  "asset_type" TEXT,
  "intent_topic" TEXT
);
CREATE TABLE master_summary(
  user_id INT,
  account_id INT,
  company_name TEXT,
  email TEXT,
  first_name TEXT,
  last_name TEXT,
  job_title TEXT,
  seniority TEXT,
  persona_type TEXT,
  ga4_events,
  mc_events,
  li_events,
  spend_consumed,
  opp_count
);
