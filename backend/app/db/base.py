from datetime import datetime

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase

# Consistent constraint naming so Alembic autogenerate (used for migrations
# AFTER 0001_initial) produces stable, greppable names.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # database-schema.sql uses `timestamptz` everywhere; map plain `datetime`
    # annotations to a timezone-aware column instead of SQLAlchemy's naive default.
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }
