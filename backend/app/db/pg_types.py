"""Shared column-type helpers so every model references PG enums/JSONB the
same way. Enums use create_type=False because the actual `CREATE TYPE` runs
in the Alembic migration (see db/alembic/versions/0001_initial.py) — letting
SQLAlchemy manage enum DDL here would double-create them.
"""

import enum

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls: type[enum.Enum], pg_name: str) -> SAEnum:
    return SAEnum(
        enum_cls,
        name=pg_name,
        create_type=False,
        values_callable=lambda e: [member.value for member in e],
    )
