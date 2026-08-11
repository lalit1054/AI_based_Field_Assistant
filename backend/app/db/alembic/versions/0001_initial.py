"""initial schema

Hand-authored to reproduce database-schema.sql exactly (enums, triggers,
the ticket-number sequence/function, the HNSW vector index, and the
sla_policies seed rows) rather than relying on autogenerate, which cannot
express trigger/function DDL. Keep this file and database-schema.sql in
sync if either changes.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-08

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---- extensions ----
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ---- enum types ----
    op.execute("CREATE TYPE machine_type AS ENUM ('VISUAL_INSPECTION')")
    op.execute("CREATE TYPE os_type AS ENUM ('linux', 'windows')")
    op.execute("CREATE TYPE machine_status AS ENUM ('active', 'maintenance', 'decommissioned')")
    op.execute(
        "CREATE TYPE user_role AS ENUM "
        "('operator', 'field_tech', 'support_l2', 'support_l3', 'plant_manager', "
        "'admin', 'company_viewer')"
    )
    op.execute(
        "CREATE TYPE session_status AS ENUM "
        "('active', 'resolved_self', 'ticket_raised', 'abandoned')"
    )
    op.execute("CREATE TYPE chat_role AS ENUM ('user', 'assistant', 'tool', 'system')")
    op.execute(
        "CREATE TYPE ticket_status AS ENUM "
        "('new', 'assigned', 'in_progress', 'on_hold', 'resolved', 'closed', 'reopened')"
    )
    op.execute("CREATE TYPE ticket_priority AS ENUM ('low', 'medium', 'high', 'critical')")
    op.execute(
        "CREATE TYPE issue_category AS ENUM "
        "('connectivity', 'app_crash', 'api_error', 'camera_image', 'data_mismatch', "
        "'hardware', 'power', 'other')"
    )
    op.execute("CREATE TYPE attachment_kind AS ENUM ('photo', 'video', 'log_bundle', 'document')")
    op.execute(
        "CREATE TYPE kb_doc_type AS ENUM "
        "('runbook', 'sop', 'oem_manual', 'known_error', 'resolved_ticket', 'faq')"
    )
    op.execute("CREATE TYPE notify_channel AS ENUM ('whatsapp', 'sms', 'email', 'in_app')")
    op.execute("CREATE TYPE notify_status AS ENUM ('pending', 'sent', 'delivered', 'failed')")

    # ---- updated_at trigger function ----
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
        BEGIN
          NEW.updated_at = now();
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
        """
    )

    # ================= 1. MACHINE REGISTRY =================

    op.execute(
        """
        CREATE TABLE companies (
          id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          code          text NOT NULL UNIQUE,
          name          text NOT NULL,
          contact_name  text,
          contact_phone text,
          contact_email text,
          is_active     boolean NOT NULL DEFAULT true,
          created_at    timestamptz NOT NULL DEFAULT now(),
          updated_at    timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE TRIGGER trg_companies_updated BEFORE UPDATE ON companies "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )

    op.execute(
        """
        CREATE TABLE plants (
          id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          company_id  uuid NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
          code        text NOT NULL UNIQUE,
          name        text NOT NULL,
          address     text,
          latitude    numeric(9,6),
          longitude   numeric(9,6),
          timezone    text NOT NULL DEFAULT 'Asia/Kolkata',
          is_active   boolean NOT NULL DEFAULT true,
          created_at  timestamptz NOT NULL DEFAULT now(),
          updated_at  timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_plants_company ON plants(company_id)")
    op.execute(
        "CREATE TRIGGER trg_plants_updated BEFORE UPDATE ON plants "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )

    op.execute(
        """
        CREATE TABLE lines (
          id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          plant_id    uuid NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
          line_number int  NOT NULL,
          name        text,
          is_active   boolean NOT NULL DEFAULT true,
          UNIQUE (plant_id, line_number)
        )
        """
    )
    op.execute("CREATE INDEX idx_lines_plant ON lines(plant_id)")

    op.execute(
        """
        CREATE TABLE machines (
          id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          plant_id     uuid NOT NULL REFERENCES plants(id) ON DELETE RESTRICT,
          line_id      uuid REFERENCES lines(id) ON DELETE SET NULL,
          machine_type machine_type NOT NULL,
          name         text NOT NULL,
          hostname     text,
          ip_address   inet,
          os           os_type,
          app_version  text,
          device_model text,
          log_labels   jsonb NOT NULL DEFAULT '{}',
          status       machine_status NOT NULL DEFAULT 'active',
          installed_at date,
          notes        text,
          created_at   timestamptz NOT NULL DEFAULT now(),
          updated_at   timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_machines_plant ON machines(plant_id)")
    op.execute("CREATE INDEX idx_machines_line ON machines(line_id)")
    op.execute("CREATE INDEX idx_machines_type ON machines(machine_type)")
    op.execute(
        "CREATE TRIGGER trg_machines_updated BEFORE UPDATE ON machines "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )

    op.execute(
        """
        CREATE TABLE qr_tokens (
          id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          machine_id uuid NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
          token      text NOT NULL UNIQUE,
          is_active  boolean NOT NULL DEFAULT true,
          created_at timestamptz NOT NULL DEFAULT now(),
          revoked_at timestamptz
        )
        """
    )
    op.execute("CREATE INDEX idx_qr_tokens_machine ON qr_tokens(machine_id)")

    # ================= 2. USERS, AUTH & ACCESS =================

    op.execute(
        """
        CREATE TABLE users (
          id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          phone         text UNIQUE,
          email         text UNIQUE,
          full_name     text NOT NULL,
          role          user_role NOT NULL DEFAULT 'operator',
          password_hash text,
          language      text NOT NULL DEFAULT 'en',
          is_active     boolean NOT NULL DEFAULT true,
          last_login_at timestamptz,
          created_at    timestamptz NOT NULL DEFAULT now(),
          updated_at    timestamptz NOT NULL DEFAULT now(),
          CHECK (phone IS NOT NULL OR email IS NOT NULL)
        )
        """
    )
    op.execute(
        "CREATE TRIGGER trg_users_updated BEFORE UPDATE ON users "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )

    op.execute(
        """
        CREATE TABLE user_plant_access (
          user_id  uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          plant_id uuid NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
          PRIMARY KEY (user_id, plant_id)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE otp_codes (
          id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          phone       text NOT NULL,
          code_hash   text NOT NULL,
          purpose     text NOT NULL DEFAULT 'login',
          expires_at  timestamptz NOT NULL,
          consumed_at timestamptz,
          attempts    int NOT NULL DEFAULT 0,
          created_at  timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_otp_phone ON otp_codes(phone, created_at DESC)")

    op.execute(
        """
        CREATE TABLE refresh_tokens (
          id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          token_hash text NOT NULL UNIQUE,
          expires_at timestamptz NOT NULL,
          revoked_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    # ================= 3. TROUBLESHOOTING SESSIONS (CHAT) =================

    op.execute(
        """
        CREATE TABLE chat_sessions (
          id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          machine_id         uuid NOT NULL REFERENCES machines(id) ON DELETE RESTRICT,
          user_id            uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
          status             session_status NOT NULL DEFAULT 'active',
          category           issue_category,
          langgraph_thread_id text,
          diagnosis_summary  text,
          token_cost_usd     numeric(10,4) DEFAULT 0,
          user_rating        smallint CHECK (user_rating BETWEEN 1 AND 5),
          started_at         timestamptz NOT NULL DEFAULT now(),
          ended_at           timestamptz
        )
        """
    )
    op.execute("CREATE INDEX idx_sessions_machine ON chat_sessions(machine_id, started_at DESC)")
    op.execute("CREATE INDEX idx_sessions_user  ON chat_sessions(user_id, started_at DESC)")

    op.execute(
        """
        CREATE TABLE chat_messages (
          id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          session_id uuid NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
          role       chat_role NOT NULL,
          content    text NOT NULL DEFAULT '',
          tool_name  text,
          metadata   jsonb NOT NULL DEFAULT '{}',
          created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_messages_session ON chat_messages(session_id, created_at)")

    # ================= 4. TICKETING =================

    op.execute(
        """
        CREATE TABLE sla_policies (
          id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          name               text NOT NULL,
          priority           ticket_priority NOT NULL,
          response_minutes   int NOT NULL,
          resolution_minutes int NOT NULL,
          UNIQUE (priority)
        )
        """
    )

    op.execute("CREATE SEQUENCE ticket_number_seq")

    op.execute(
        """
        CREATE TABLE tickets (
          id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          ticket_number     text NOT NULL UNIQUE,
          machine_id        uuid NOT NULL REFERENCES machines(id) ON DELETE RESTRICT,
          session_id        uuid REFERENCES chat_sessions(id) ON DELETE SET NULL,
          reporter_id       uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
          assignee_id       uuid REFERENCES users(id) ON DELETE SET NULL,
          status            ticket_status NOT NULL DEFAULT 'new',
          priority          ticket_priority NOT NULL DEFAULT 'medium',
          category          issue_category NOT NULL DEFAULT 'other',
          title             text NOT NULL,
          description       text,
          diagnosis_summary text,
          sla_policy_id     uuid REFERENCES sla_policies(id),
          first_response_due_at timestamptz,
          resolution_due_at timestamptz,
          first_responded_at timestamptz,
          resolved_at       timestamptz,
          closed_at         timestamptz,
          resolution_notes  text,
          created_at        timestamptz NOT NULL DEFAULT now(),
          updated_at        timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_tickets_status   ON tickets(status)")
    op.execute("CREATE INDEX idx_tickets_machine  ON tickets(machine_id)")
    op.execute(
        "CREATE INDEX idx_tickets_assignee ON tickets(assignee_id) WHERE assignee_id IS NOT NULL"
    )
    op.execute("CREATE INDEX idx_tickets_created  ON tickets(created_at DESC)")
    op.execute(
        "CREATE TRIGGER trg_tickets_updated BEFORE UPDATE ON tickets "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION assign_ticket_number() RETURNS trigger AS $$
        BEGIN
          IF NEW.ticket_number IS NULL OR NEW.ticket_number = '' THEN
            NEW.ticket_number := 'TKT-' || to_char(now(), 'YYYY') || '-' ||
                                 lpad(nextval('ticket_number_seq')::text, 6, '0');
          END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        "CREATE TRIGGER trg_ticket_number BEFORE INSERT ON tickets "
        "FOR EACH ROW EXECUTE FUNCTION assign_ticket_number()"
    )

    op.execute(
        """
        CREATE TABLE ticket_comments (
          id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          ticket_id   uuid NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
          author_id   uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
          body        text NOT NULL,
          is_internal boolean NOT NULL DEFAULT false,
          created_at  timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_comments_ticket ON ticket_comments(ticket_id, created_at)")

    op.execute(
        """
        CREATE TABLE ticket_status_history (
          id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          ticket_id  uuid NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
          from_status ticket_status,
          to_status  ticket_status NOT NULL,
          changed_by uuid REFERENCES users(id),
          changed_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_status_hist_ticket ON ticket_status_history(ticket_id, changed_at)"
    )

    # ================= 5. ATTACHMENTS =================

    op.execute(
        """
        CREATE TABLE attachments (
          id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          kind         attachment_kind NOT NULL,
          ticket_id    uuid REFERENCES tickets(id) ON DELETE CASCADE,
          session_id   uuid REFERENCES chat_sessions(id) ON DELETE CASCADE,
          message_id   uuid REFERENCES chat_messages(id) ON DELETE SET NULL,
          object_key   text NOT NULL,
          file_name    text NOT NULL,
          content_type text NOT NULL,
          size_bytes   bigint NOT NULL,
          uploaded_by  uuid REFERENCES users(id),
          created_at   timestamptz NOT NULL DEFAULT now(),
          CHECK (ticket_id IS NOT NULL OR session_id IS NOT NULL)
        )
        """
    )
    op.execute("CREATE INDEX idx_attachments_ticket  ON attachments(ticket_id)")
    op.execute("CREATE INDEX idx_attachments_session ON attachments(session_id)")

    # ================= 6. KNOWLEDGE BASE (RAG) =================

    op.execute(
        """
        CREATE TABLE kb_documents (
          id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          title          text NOT NULL,
          doc_type       kb_doc_type NOT NULL,
          machine_type   machine_type,
          source_object_key text,
          version        int NOT NULL DEFAULT 1,
          is_active      boolean NOT NULL DEFAULT true,
          created_by     uuid REFERENCES users(id),
          created_at     timestamptz NOT NULL DEFAULT now(),
          updated_at     timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_kb_docs_machine_type ON kb_documents(machine_type) WHERE is_active"
    )
    op.execute(
        "CREATE TRIGGER trg_kb_docs_updated BEFORE UPDATE ON kb_documents "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )

    op.execute(
        """
        CREATE TABLE kb_chunks (
          id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          document_id uuid NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
          chunk_index int NOT NULL,
          content     text NOT NULL,
          embedding   vector(1024),
          metadata    jsonb NOT NULL DEFAULT '{}',
          UNIQUE (document_id, chunk_index)
        )
        """
    )
    op.execute("CREATE INDEX idx_kb_chunks_doc ON kb_chunks(document_id)")
    op.execute(
        "CREATE INDEX idx_kb_chunks_embedding ON kb_chunks USING hnsw (embedding vector_cosine_ops)"
    )

    op.execute(
        """
        CREATE TABLE known_errors (
          id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          machine_type       machine_type NOT NULL,
          category           issue_category NOT NULL,
          title              text NOT NULL,
          error_signature    text NOT NULL,
          probable_cause     text NOT NULL,
          operator_fix_steps text NOT NULL,
          engineer_fix_steps text,
          severity           ticket_priority NOT NULL DEFAULT 'medium',
          is_active          boolean NOT NULL DEFAULT true,
          hit_count          int NOT NULL DEFAULT 0,
          created_at         timestamptz NOT NULL DEFAULT now(),
          updated_at         timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_known_errors_machine_type ON known_errors(machine_type, category) "
        "WHERE is_active"
    )
    op.execute(
        "CREATE TRIGGER trg_known_errors_updated BEFORE UPDATE ON known_errors "
        "FOR EACH ROW EXECUTE FUNCTION set_updated_at()"
    )

    # ================= 7. HEALTH & HEARTBEATS =================

    op.execute(
        """
        CREATE TABLE machine_health (
          machine_id      uuid PRIMARY KEY REFERENCES machines(id) ON DELETE CASCADE,
          last_heartbeat  timestamptz,
          is_online       boolean NOT NULL DEFAULT false,
          cpu_percent     numeric(5,2),
          memory_percent  numeric(5,2),
          disk_percent    numeric(5,2),
          services        jsonb NOT NULL DEFAULT '{}',
          extra           jsonb NOT NULL DEFAULT '{}',
          updated_at      timestamptz NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE heartbeats (
          id          bigserial PRIMARY KEY,
          machine_id  uuid NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
          reported_at timestamptz NOT NULL DEFAULT now(),
          metrics     jsonb NOT NULL DEFAULT '{}'
        )
        """
    )
    op.execute("CREATE INDEX idx_heartbeats_machine ON heartbeats(machine_id, reported_at DESC)")

    # ================= 8. NOTIFICATIONS & AUDIT =================

    op.execute(
        """
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
        )
        """
    )
    op.execute("CREATE INDEX idx_notifications_user ON notifications(user_id, created_at DESC)")

    op.execute(
        """
        CREATE TABLE audit_log (
          id          bigserial PRIMARY KEY,
          user_id     uuid REFERENCES users(id) ON DELETE SET NULL,
          action      text NOT NULL,
          entity_type text,
          entity_id   uuid,
          ip_address  inet,
          user_agent  text,
          details     jsonb NOT NULL DEFAULT '{}',
          created_at  timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX idx_audit_created ON audit_log(created_at DESC)")
    op.execute("CREATE INDEX idx_audit_entity  ON audit_log(entity_type, entity_id)")

    # ================= 9. SEED DATA (dev/demo) =================

    op.execute(
        """
        INSERT INTO sla_policies (name, priority, response_minutes, resolution_minutes) VALUES
          ('Critical SLA', 'critical', 15,  240),
          ('High SLA',     'high',     30,  480),
          ('Medium SLA',   'medium',   120, 1440),
          ('Low SLA',      'low',      480, 4320)
        """
    )


def downgrade() -> None:
    # Full teardown appropriate for the initial revision only.
    op.execute("DROP SCHEMA public CASCADE")
    op.execute("CREATE SCHEMA public")
