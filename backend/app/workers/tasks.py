"""ARQ task functions. Real jobs (KB ingestion, SLA timers, notifications)
land in later milestones — this placeholder keeps the worker process alive
and importable from Milestone 1 onward.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import update

from app.db.engine import AsyncSessionLocal
from app.db.models import MachineHealth

# a machine with no heartbeat in this long is considered offline even though
# no explicit "went offline" event was ever reported
STALE_AFTER = timedelta(minutes=5)


async def noop(ctx: dict) -> str:
    return "ok"


async def mark_stale_machines_offline(ctx: dict) -> int:
    """Milestone 5: periodic sweep — flips is_online=false for any machine
    whose last heartbeat is older than STALE_AFTER (or that never reported
    one but was previously marked online)."""
    cutoff = datetime.now(timezone.utc) - STALE_AFTER
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            update(MachineHealth)
            .where(MachineHealth.is_online.is_(True), MachineHealth.last_heartbeat < cutoff)
            .values(is_online=False)
        )
        await db.commit()
        return result.rowcount  # type: ignore[attr-defined]
