"""Log fetching for a machine's recent activity, used for diagnostics.

Real branch is a minimal Loki query wrapper — not exercised without a live
Loki instance. Dev/test default (`settings.loki_fake=True`) returns canned
lines from app/tests/fixtures/logs/<machine_type>.log so the rest of the
system (and later, the diagnostic agent) can be built against realistic data
without a running log stack.
"""

from pathlib import Path

import httpx

from app.config import get_settings
from app.db.enums import MachineType

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "logs"


def _fake_log_lines(machine_type: MachineType) -> list[str]:
    path = FIXTURES_DIR / f"{machine_type.value.lower()}.log"
    if not path.exists():
        return []
    return path.read_text().splitlines()


async def fetch_recent_logs(
    machine_type: MachineType, hostname: str | None, limit: int = 100
) -> list[str]:
    settings = get_settings()
    if settings.loki_fake:
        return _fake_log_lines(machine_type)[-limit:]

    params: dict[str, str | int] = {"query": f'{{host="{hostname}"}}', "limit": limit}
    async with httpx.AsyncClient(base_url=settings.loki_url, timeout=5.0) as client:
        resp = await client.get("/loki/api/v1/query_range", params=params)
        resp.raise_for_status()
        data = resp.json()
        lines: list[str] = []
        for stream in data.get("data", {}).get("result", []):
            for _ts, line in stream.get("values", []):
                lines.append(line)
        return lines[-limit:]
