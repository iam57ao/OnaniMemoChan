from dataclasses import dataclass
from datetime import datetime, timedelta

from .repositories import RecordRepository
from .ui import bucketize_hours, pick_top_bucket
from .utils import parse_iso, utc_now


@dataclass(frozen=True)
class StatsSummary:
    total: int
    avg_week: float | None
    avg_month: float | None
    top_bucket: str | None
    avg_interval: timedelta | None
    last_ago: timedelta | None


class StatsService:
    def __init__(self, records: RecordRepository) -> None:
        self._records = records

    def build_summary(self, user_id: int, days: int) -> StatsSummary:
        now = utc_now()
        start = now - timedelta(days=days)
        entries = self._records.list_records_in_range(user_id, start, now)
        total = len(entries)

        first_record = self._records.get_first_record_time(user_id)
        avg_week = self._average_rate(first_record, now, 7, user_id)
        avg_month = self._average_rate(first_record, now, 30, user_id)

        hours = []
        for entry in entries:
            local_dt = parse_iso(entry["timestamp_local"])
            hours.append(local_dt.hour)
        bucket_counts = bucketize_hours(hours)
        top_bucket = pick_top_bucket(bucket_counts)

        avg_interval, last_ago = self._interval_stats(entries, now)
        return StatsSummary(
            total=total,
            avg_week=avg_week,
            avg_month=avg_month,
            top_bucket=top_bucket,
            avg_interval=avg_interval,
            last_ago=last_ago,
        )

    def _average_rate(
        self,
        first_record: datetime | None,
        now: datetime,
        period_days: int,
        user_id: int,
    ) -> float | None:
        if not first_record:
            return None
        elapsed = now - first_record
        if elapsed < timedelta(days=period_days):
            return None
        total = self._records.count_all_records(user_id)
        periods = elapsed / timedelta(days=period_days)
        if periods <= 0:
            return None
        return total / periods

    def _interval_stats(
        self, entries: list[dict[str, str]], now: datetime
    ) -> tuple[timedelta | None, timedelta | None]:
        if len(entries) < 2:
            last_ago = None
            if entries:
                last_ago = now - parse_iso(entries[-1]["timestamp_utc"])
            return None, last_ago
        timestamps = [parse_iso(entry["timestamp_utc"]) for entry in entries]
        diffs = [
            later - earlier for earlier, later in zip(timestamps, timestamps[1:], strict=False)
        ]
        avg_interval = sum(diffs, timedelta()) / len(diffs)
        last_ago = now - timestamps[-1]
        return avg_interval, last_ago
