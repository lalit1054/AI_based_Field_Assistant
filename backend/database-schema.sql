-- ============================================================================
-- AI-Assisted Manufacturing Plant Troubleshooting & Ticketing Platform
-- PostgreSQL 16+ Schema  |  requires: pgvector, pgcrypto
-- Apply with: psql -U app -d troubleshoot -f database-schema.sql
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS vector;      -- pgvector for RAG embeddings
CREATE EXTENSION IF NOT EXISTS pgcrypto;    -- gen_random_uuid()

-- ----------------------------------------------------------------------------
-- ENUM TYPES
-- ----------------------------------------------------------------------------
CREATE TYPE machine_type    AS ENUM ('VISUAL_INSPECTION');
CREATE TYPE os_type         AS ENUM ('linux', 'windows');
CREATE TYPE machine_status  AS ENUM ('active', 'maintenance', 'decommissioned');
CREATE TYPE user_role       AS ENUM ('operator', 'field_tech', 'support_l2', 'support_l3', 'plant_manager', 'admin', 'company_viewer');
CREATE TYPE session_status  AS ENUM ('active', 'resolved_self', 'ticket_raised', 'abandoned');
CREATE TYPE chat_role       AS ENUM ('user', 'assistant', 'tool', 'system');
CREATE TYPE ticket_status   AS ENUM ('new', 'assigned', 'in_progress', 'on_hold', 'resolved', 'closed', 'reopened');
CREATE TYPE ticket_priority AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE issue_category  AS ENUM ('connectivity', 'app_crash', 'api_error', 'camera_image', 'data_mismatch', 'hardware', 'power', 'other');
CREATE TYPE attachment_kind AS ENUM ('photo', 'video', 'log_bundle', 'document');
CREATE TYPE kb_doc_type     AS ENUM ('runbook', 'sop', 'oem_manual', 'known_error', 'resolved_ticket', 'faq');
CREATE TYPE notify_channel  AS ENUM ('whatsapp', 'sms', 'email', 'in_app');
CREATE TYPE notify_status   AS ENUM ('pending', 'sent', 'delivered', 'failed');

-- ----------------------------------------------------------------------------
-- COMMON: updated_at trigger
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

-- ============================================================================
-- 1. MACHINE REGISTRY
-- ============================================================================

CREATE TABLE companies (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  code          text NOT NULL UNIQUE,               -- short code e.g. 'JBM'
  name          text NOT NULL,
  contact_name  text,
  contact_phone text,
  contact_email text,
  is_active     boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE TRIGGER trg_companies_updated BEFORE UPDATE ON companies
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE plants (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  company_id  uuid NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
  code        text NOT NULL UNIQUE,                 -- e.g. 'JBM-3XO-NSK'
  name        text NOT NULL,                        -- e.g. '3xo Nashik'
  address     text,
  latitude    numeric(9,6),
  longitude   numeric(9,6),
  timezone    text NOT NULL DEFAULT 'Asia/Kolkata',
  is_active   boolean NOT NULL DEFAULT true,
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_plants_company ON plants(company_id);
CREATE TRIGGER trg_plants_updated BEFORE UPDATE ON plants
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE lines (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  plant_id    uuid NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
  line_number int  NOT NULL,
  name        text,                                  -- e.g. 'Line 1'
  is_active   boolean NOT NULL DEFAULT true,
  UNIQUE (plant_id, line_number)
);
CREATE INDEX idx_lines_plant ON lines(plant_id);

CREATE TABLE machines (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  plant_id     uuid NOT NULL REFERENCES plants(id) ON DELETE RESTRICT,
  line_id      uuid REFERENCES lines(id) ON DELETE SET NULL,  -- NULL for plant-level machines
  machine_type machine_type NOT NULL,
  name         text NOT NULL,                        -- e.g. 'VI 12 parts inspection system'
  hostname     text,
  ip_address   inet,
  os           os_type,
  app_version  text,
  device_model text,                                 -- camera/PLC/controller model
  log_labels   jsonb NOT NULL DEFAULT '{}',          -- labels used in Loki: {"plant":"JBM-3XO-NSK","line":"1","machine":"vi12"}
  status       machine_status NOT NULL DEFAULT 'active',
  installed_at date,
  notes        text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_machines_plant ON machines(plant_id);
CREATE INDEX idx_machines_line ON machines(line_id);
CREATE INDEX idx_machines_type ON machines(machine_type);
CREATE TRIGGER trg_machines_updated BEFORE UPDATE ON machines
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Signed QR tokens: URL is /a/<token>. Random, revocable, rotatable.
CREATE TABLE qr_tokens (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  machine_id uuid NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
  token      text NOT NULL UNIQUE,                   -- 22+ char url-safe random
  is_active  boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  revoked_at timestamptz
);
CREATE INDEX idx_qr_tokens_machine ON qr_tokens(machine_id);

-- ============================================================================
-- 2. USERS, AUTH & ACCESS
-- ============================================================================

CREATE TABLE users (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  phone         text UNIQUE,                         -- E.164, primary identity for operators
  email         text UNIQUE,
  full_name     text NOT NULL,
  role          user_role NOT NULL DEFAULT 'operator',
  password_hash text,                                -- staff logins; NULL for phone-only users
  language      text NOT NULL DEFAULT 'en',          -- 'en' | 'hi'
  is_active     boolean NOT NULL DEFAULT true,
  last_login_at timestamptz,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  CHECK (phone IS NOT NULL OR email IS NOT NULL)
);
CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Which plants a user may see/report on (admins bypass this)
CREATE TABLE user_plant_access (
  user_id  uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plant_id uuid NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
  PRIMARY KEY (user_id, plant_id)
);

CREATE TABLE refresh_tokens (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash text NOT NULL UNIQUE,
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- ============================================================================
-- 3. TROUBLESHOOTING SESSIONS (CHAT)
-- ============================================================================

CREATE TABLE chat_sessions (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  machine_id         uuid NOT NULL REFERENCES machines(id) ON DELETE RESTRICT,
  user_id            uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  status             session_status NOT NULL DEFAULT 'active',
  category           issue_category,                 -- set by triage node
  langgraph_thread_id text,                          -- LangGraph checkpoint thread
  diagnosis_summary  text,                           -- final diagnosis by agent
  token_cost_usd     numeric(10,4) DEFAULT 0,
  user_rating        smallint CHECK (user_rating BETWEEN 1 AND 5),
  started_at         timestamptz NOT NULL DEFAULT now(),
  ended_at           timestamptz
);
CREATE INDEX idx_sessions_machine ON chat_sessions(machine_id, started_at DESC);
CREATE INDEX idx_sessions_user  ON chat_sessions(user_id, started_at DESC);

CREATE TABLE chat_messages (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
  role       chat_role NOT NULL,
  content    text NOT NULL DEFAULT '',
  tool_name  text,                                   -- when role='tool'
  metadata   jsonb NOT NULL DEFAULT '{}',            -- tool args/results refs, model, latency
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_messages_session ON chat_messages(session_id, created_at);

-- ============================================================================
-- 4. TICKETING
-- ============================================================================

CREATE TABLE sla_policies (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name               text NOT NULL,
  priority           ticket_priority NOT NULL,
  response_minutes   int NOT NULL,                   -- time to first response
  resolution_minutes int NOT NULL,                   -- time to resolution
  UNIQUE (priority)
);

CREATE SEQUENCE ticket_number_seq;

CREATE TABLE tickets (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_number     text NOT NULL UNIQUE,            -- 'TKT-2026-000123', set by trigger
  machine_id        uuid NOT NULL REFERENCES machines(id) ON DELETE RESTRICT,
  session_id        uuid REFERENCES chat_sessions(id) ON DELETE SET NULL,
  reporter_id       uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  assignee_id       uuid REFERENCES users(id) ON DELETE SET NULL,
  status            ticket_status NOT NULL DEFAULT 'new',
  priority          ticket_priority NOT NULL DEFAULT 'medium',
  category          issue_category NOT NULL DEFAULT 'other',
  title             text NOT NULL,
  description       text,
  diagnosis_summary text,                            -- copied from agent at creation
  sla_policy_id     uuid REFERENCES sla_policies(id),
  first_response_due_at timestamptz,
  resolution_due_at timestamptz,
  first_responded_at timestamptz,
  resolved_at       timestamptz,
  closed_at         timestamptz,
  resolution_notes  text,
  created_at        timestamptz NOT NULL DEFAULT now(),
  updated_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_tickets_status   ON tickets(status);
CREATE INDEX idx_tickets_machine  ON tickets(machine_id);
CREATE INDEX idx_tickets_assignee ON tickets(assignee_id) WHERE assignee_id IS NOT NULL;
CREATE INDEX idx_tickets_created  ON tickets(created_at DESC);
CREATE TRIGGER trg_tickets_updated BEFORE UPDATE ON tickets
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE OR REPLACE FUNCTION assign_ticket_number() RETURNS trigger AS $$
BEGIN
  IF NEW.ticket_number IS NULL OR NEW.ticket_number = '' THEN
    NEW.ticket_number := 'TKT-' || to_char(now(), 'YYYY') || '-' ||
                         lpad(nextval('ticket_number_seq')::text, 6, '0');
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;
CREATE TRIGGER trg_ticket_number BEFORE INSERT ON tickets
  FOR EACH ROW EXECUTE FUNCTION assign_ticket_number();

CREATE TABLE ticket_comments (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_id   uuid NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  author_id   uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
  body        text NOT NULL,
  is_internal boolean NOT NULL DEFAULT false,        -- hidden from reporter/company
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_comments_ticket ON ticket_comments(ticket_id, created_at);

-- Ticket status history for SLA reporting/audit
CREATE TABLE ticket_status_history (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_id  uuid NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
  from_status ticket_status,
  to_status  ticket_status NOT NULL,
  changed_by uuid REFERENCES users(id),
  changed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_status_hist_ticket ON ticket_status_history(ticket_id, changed_at);

-- ============================================================================
-- 5. ATTACHMENTS (photos/videos/log bundles) — stored in MinIO/S3
-- ============================================================================

CREATE TABLE attachments (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  kind         attachment_kind NOT NULL,
  ticket_id    uuid REFERENCES tickets(id) ON DELETE CASCADE,
  session_id   uuid REFERENCES chat_sessions(id) ON DELETE CASCADE,
  message_id   uuid REFERENCES chat_messages(id) ON DELETE SET NULL,
  object_key   text NOT NULL,                        -- S3/MinIO key
  file_name    text NOT NULL,
  content_type text NOT NULL,
  size_bytes   bigint NOT NULL,
  uploaded_by  uuid REFERENCES users(id),
  created_at   timestamptz NOT NULL DEFAULT now(),
  CHECK (ticket_id IS NOT NULL OR session_id IS NOT NULL)
);
CREATE INDEX idx_attachments_ticket  ON attachments(ticket_id);
CREATE INDEX idx_attachments_session ON attachments(session_id);

-- ============================================================================
-- 6. KNOWLEDGE BASE (RAG)
-- ============================================================================

CREATE TABLE kb_documents (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  title          text NOT NULL,
  doc_type       kb_doc_type NOT NULL,
  machine_type   machine_type,                       -- NULL = applies to all machines
  source_object_key text,                            -- original PDF/DOCX in object storage
  version        int NOT NULL DEFAULT 1,
  is_active      boolean NOT NULL DEFAULT true,
  created_by     uuid REFERENCES users(id),
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_kb_docs_machine_type ON kb_documents(machine_type) WHERE is_active;
CREATE TRIGGER trg_kb_docs_updated BEFORE UPDATE ON kb_documents
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- NOTE: vector dimension must match your embedding model
-- (1024 = bge-m3 / voyage; use 1536/3072 for OpenAI models — change before applying)
CREATE TABLE kb_chunks (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id uuid NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
  chunk_index int NOT NULL,
  content     text NOT NULL,
  embedding   vector(1024),
  metadata    jsonb NOT NULL DEFAULT '{}',           -- page, section, category tags
  UNIQUE (document_id, chunk_index)
);
CREATE INDEX idx_kb_chunks_doc ON kb_chunks(document_id);
CREATE INDEX idx_kb_chunks_embedding ON kb_chunks
  USING hnsw (embedding vector_cosine_ops);

-- Curated known-error database: deterministic first-line matching before LLM
CREATE TABLE known_errors (
  id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  machine_type       machine_type NOT NULL,
  category           issue_category NOT NULL,
  title              text NOT NULL,
  error_signature    text NOT NULL,                  -- regex matched against logs
  probable_cause     text NOT NULL,
  operator_fix_steps text NOT NULL,                  -- markdown, operator-safe only
  engineer_fix_steps text,                           -- markdown, shown to staff roles
  severity           ticket_priority NOT NULL DEFAULT 'medium',
  is_active          boolean NOT NULL DEFAULT true,
  hit_count          int NOT NULL DEFAULT 0,
  created_at         timestamptz NOT NULL DEFAULT now(),
  updated_at         timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_known_errors_machine_type ON known_errors(machine_type, category) WHERE is_active;
CREATE TRIGGER trg_known_errors_updated BEFORE UPDATE ON known_errors
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- ============================================================================
-- 7. HEALTH & HEARTBEATS
-- ============================================================================

-- Latest state per machine (fast lookups for the health card)
CREATE TABLE machine_health (
  machine_id      uuid PRIMARY KEY REFERENCES machines(id) ON DELETE CASCADE,
  last_heartbeat  timestamptz,
  is_online       boolean NOT NULL DEFAULT false,
  cpu_percent     numeric(5,2),
  memory_percent  numeric(5,2),
  disk_percent    numeric(5,2),
  services        jsonb NOT NULL DEFAULT '{}',       -- {"vision-engine":"running","api":"stopped"}
  extra           jsonb NOT NULL DEFAULT '{}',
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- Time-series history (consider partitioning by month at scale)
CREATE TABLE heartbeats (
  id          bigserial PRIMARY KEY,
  machine_id  uuid NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
  reported_at timestamptz NOT NULL DEFAULT now(),
  metrics     jsonb NOT NULL DEFAULT '{}'
);
CREATE INDEX idx_heartbeats_machine ON heartbeats(machine_id, reported_at DESC);

-- ============================================================================
-- 8. NOTIFICATIONS & AUDIT
-- ============================================================================

CREATE TABLE notifications (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  ticket_id  uuid REFERENCES tickets(id) ON DELETE SET NULL,
  channel    notify_channel NOT NULL,
  status     notify_status NOT NULL DEFAULT 'pending',
  subject    text,
  payload    jsonb NOT NULL DEFAULT '{}',
  sent_at    timestamptz,
  error      text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_notifications_user ON notifications(user_id, created_at DESC);

CREATE TABLE audit_log (
  id          bigserial PRIMARY KEY,
  user_id     uuid REFERENCES users(id) ON DELETE SET NULL,
  action      text NOT NULL,                         -- 'qr_scanned','ticket_created','kb_uploaded',...
  entity_type text,
  entity_id   uuid,
  ip_address  inet,
  user_agent  text,
  details     jsonb NOT NULL DEFAULT '{}',
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);
CREATE INDEX idx_audit_entity  ON audit_log(entity_type, entity_id);

-- ============================================================================
-- 9. SEED DATA (dev/demo)
-- ============================================================================

INSERT INTO sla_policies (name, priority, response_minutes, resolution_minutes) VALUES
  ('Critical SLA', 'critical', 15,  240),
  ('High SLA',     'high',     30,  480),
  ('Medium SLA',   'medium',   120, 1440),
  ('Low SLA',      'low',      480, 4320);
