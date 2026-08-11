"""drop otp_codes

Login no longer requires OTP verification: /auth/login-phone logs a
phone straight in (self-registering an operator on first use), so the
otp_codes table and its index are no longer written to or read.

Revision ID: 0002_drop_otp_codes
Revises: 0001_initial
Create Date: 2026-07-22

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_drop_otp_codes"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_otp_phone")
    op.execute("DROP TABLE IF EXISTS otp_codes")


def downgrade() -> None:
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
