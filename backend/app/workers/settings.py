from arq.connections import RedisSettings
from arq.cron import cron

from app.config import get_settings
from app.workers.tasks import mark_stale_machines_offline, noop

settings = get_settings()


class WorkerSettings:
    functions = [noop, mark_stale_machines_offline]
    cron_jobs = [cron(mark_stale_machines_offline, minute=set(range(0, 60, 5)))]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
