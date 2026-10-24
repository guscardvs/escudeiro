"""Regression tests for the Rust cron expression (src/cronjob.rs)."""

from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from escudeiro.escudeiro_pyrs import cronjob

SUNDAY, MONDAY, SATURDAY = 6, 0, 5  # datetime.weekday()


@pytest.mark.parametrize(
    ("expression", "weekdays"),
    [
        ("0 9 * * 0", {SUNDAY}),
        ("0 9 * * 7", {SUNDAY}),
        ("0 9 * * SUN", {SUNDAY}),
        ("0 9 * * 1", {MONDAY}),
        ("0 9 * * mon", {MONDAY}),
        ("0 9 * * 6", {SATURDAY}),
        ("0 9 * * 1-5", {0, 1, 2, 3, 4}),
        ("0 9 * * MON-FRI", {0, 1, 2, 3, 4}),
        ("0 9 * * 5-7", {4, SATURDAY, SUNDAY}),
        ("0 9 * * 0,6", {SUNDAY, SATURDAY}),
        ("0 9 * * *", set(range(7))),
    ],
)
def test_crontab_weekdays(expression: str, weekdays: set[int]):
    runs = cronjob.CronExpr(expression, UTC).upcoming_runs(30)
    assert {run.weekday() for run in runs} == weekdays
    assert all(run.hour == 9 and run.minute == 0 for run in runs)


@pytest.mark.parametrize(
    "expression",
    [
        "* * * *",
        "0 * * * * *",  # 6 fields used to be silently reinterpreted
        "0 0 9 * * 1 2030",
        "0 9 * * 8",
        "0 9 * * MONDAY",
        "0 9 * * 5-1",
        "not a cron",
    ],
)
def test_invalid_expressions(expression: str):
    with pytest.raises(ValueError, match="cron expression"):
        cronjob.CronExpr(expression, UTC)


def test_zoneinfo_is_accepted_and_follows_dst():
    tz = ZoneInfo("Europe/Berlin")
    cron = cronjob.CronExpr("0 9 * * *", tz)
    assert cron.timezone is tz
    runs = cron.upcoming_runs(400)  # covers both DST transitions
    assert {run.astimezone(tz).hour for run in runs} == {9}
    assert len({run.utcoffset() for run in runs}) == 2


def test_iana_name_is_accepted():
    cron = cronjob.CronExpr("0 9 * * *", "America/New_York")
    runs = cron.upcoming_runs(400)
    tz = ZoneInfo("America/New_York")
    assert {run.astimezone(tz).hour for run in runs} == {9}


def test_fixed_offset_keeps_its_offset():
    tz = timezone(timedelta(hours=-3))
    cron = cronjob.CronExpr("0 9 * * *", tz)
    assert cron.timezone is tz
    assert {(r.hour, r.utcoffset()) for r in cron.upcoming_runs(5)} == {
        (9, timedelta(hours=-3))
    }
    assert cron.next_run.utcoffset() == timedelta(hours=-3)


def test_invalid_timezone():
    with pytest.raises(TypeError):
        cronjob.CronExpr("* * * * *", 3)  # pyright: ignore[reportArgumentType]
    with pytest.raises(ValueError, match="timezone"):
        cronjob.CronExpr("* * * * *", "Not/AZone")


def test_matches_ignores_seconds():
    cron = cronjob.CronExpr("0 9 * * 1", UTC)
    assert cron.matches(datetime(2025, 1, 6, 9, 0, 0, tzinfo=UTC))
    assert cron.matches(datetime(2025, 1, 6, 9, 0, 37, 500, tzinfo=UTC))
    assert not cron.matches(datetime(2025, 1, 6, 9, 1, 0, tzinfo=UTC))
    assert not cron.matches(datetime(2025, 1, 7, 9, 0, 0, tzinfo=UTC))  # Tue


def test_matches_evaluates_in_the_cron_timezone():
    tz = ZoneInfo("Asia/Tokyo")
    cron = cronjob.CronExpr("30 9 * * *", tz)
    assert cron.matches(datetime(2025, 1, 1, 0, 30, tzinfo=UTC))
    assert not cron.matches(datetime(2025, 1, 1, 9, 30, tzinfo=UTC))


def test_update_after_is_strictly_after_and_uses_cron_timezone():
    cron = cronjob.CronExpr("* * * * *", UTC)
    cron.update_after(datetime(2025, 1, 1, 10, 0, 0, 200_000, tzinfo=UTC))
    assert cron.next_run == datetime(2025, 1, 1, 10, 1, tzinfo=UTC)

    tz = timezone(timedelta(hours=-3))
    cron = cronjob.CronExpr("0 9 * * *", tz)
    # 13:00 UTC is 10:00 in UTC-3, so the next 09:00 local is tomorrow 12:00 UTC
    cron.update_after(datetime(2025, 1, 1, 13, 0, tzinfo=UTC))
    assert cron.next_run == datetime(2025, 1, 2, 12, 0, tzinfo=UTC)
    assert cron.next_run.utcoffset() == timedelta(hours=-3)


def test_update_moves_next_run_forward():
    cron = cronjob.CronExpr("* * * * *", UTC)
    before = cron.next_run
    assert before > datetime.now(UTC)
    cron.update()
    assert cron.next_run >= before
