use pyo3::pymodule;

/// Pure cron logic, kept outside the `#[pymodule]` so it can be unit tested without Python.
mod crontab {
    use chrono::{DateTime, FixedOffset, TimeZone, Timelike};
    use cron::Schedule;

    /// Translate a standard 5-field crontab expression into the 6-field form the `cron` crate parses.
    ///
    /// The crate numbers weekdays 1 = Sunday .. 7 = Saturday, crontab uses 0 or 7 = Sunday,
    /// 1 = Monday .. 6 = Saturday (or `SUN`..`SAT`), so the weekday field is expanded and renumbered.
    pub fn schedule_source(expression: &str) -> Result<String, String> {
        let fields: Vec<&str> = expression.split_whitespace().collect();
        if fields.len() != 5 {
            return Err(format!(
                "expected exactly 5 fields (minute hour day-of-month month day-of-week), got {}",
                fields.len()
            ));
        }
        let weekday = translate_weekday(fields[4])?;
        Ok(format!(
            "0 {} {} {} {} {}",
            fields[0], fields[1], fields[2], fields[3], weekday
        ))
    }

    fn weekday_value(token: &str, range_end: bool) -> Result<u32, String> {
        let named = match token.to_ascii_uppercase().as_str() {
            "SUN" => Some(if range_end { 7 } else { 0 }),
            "MON" => Some(1),
            "TUE" => Some(2),
            "WED" => Some(3),
            "THU" => Some(4),
            "FRI" => Some(5),
            "SAT" => Some(6),
            _ => None,
        };
        match named {
            Some(value) => Ok(value),
            None => match token.parse::<u32>() {
                Ok(value) if value <= 7 => Ok(value),
                _ => Err(format!("invalid day-of-week value {token:?}")),
            },
        }
    }

    fn translate_weekday(field: &str) -> Result<String, String> {
        if field == "*" || field == "?" {
            return Ok("*".to_string());
        }
        let mut days = [false; 7];
        for part in field.split(',') {
            let (range, step) = match part.split_once('/') {
                Some((range, step)) => match step.parse::<usize>() {
                    Ok(step) if step > 0 => (range, Some(step)),
                    _ => return Err(format!("invalid day-of-week step {step:?}")),
                },
                None => (part, None),
            };
            let (low, high) = if range == "*" || range == "?" {
                (0, 6)
            } else if let Some((low, high)) = range.split_once('-') {
                (weekday_value(low, false)?, weekday_value(high, true)?)
            } else {
                let low = weekday_value(range, false)?;
                (low, if step.is_some() { 6.max(low) } else { low })
            };
            if low > high {
                return Err(format!("invalid day-of-week range {part:?}"));
            }
            for value in (low..=high).step_by(step.unwrap_or(1)) {
                days[(value % 7) as usize] = true;
            }
        }
        if days.iter().all(|d| *d) {
            return Ok("*".to_string());
        }
        Ok(days
            .iter()
            .enumerate()
            .filter(|(_, on)| **on)
            .map(|(day, _)| (day + 1).to_string())
            .collect::<Vec<_>>()
            .join(","))
    }

    /// The first `n` runs strictly after `after`, evaluated in `tz`.
    pub fn runs_after<Z: TimeZone>(
        schedule: &Schedule,
        tz: &Z,
        after: &DateTime<FixedOffset>,
        n: usize,
    ) -> Vec<DateTime<FixedOffset>> {
        schedule
            .after(&after.with_timezone(tz))
            .take(n)
            .map(|run| run.fixed_offset())
            .collect()
    }

    /// Whether the minute containing `value` (seconds are ignored) is scheduled, evaluated in `tz`.
    pub fn includes_minute<Z: TimeZone>(
        schedule: &Schedule,
        tz: &Z,
        value: &DateTime<FixedOffset>,
    ) -> bool {
        value
            .with_timezone(tz)
            .with_second(0)
            .and_then(|local| local.with_nanosecond(0))
            .is_some_and(|local| schedule.includes(local))
    }

    #[cfg(test)]
    mod tests {
        use super::*;
        use chrono::{Datelike, Utc, Weekday};
        use std::str::FromStr;

        fn source(expression: &str) -> String {
            schedule_source(expression).unwrap()
        }

        #[test]
        fn weekday_table() {
            let table = [
                ("0 9 * * *", "0 0 9 * * *"),
                ("0 9 * * 0", "0 0 9 * * 1"),
                ("0 9 * * 7", "0 0 9 * * 1"),
                ("0 9 * * 1", "0 0 9 * * 2"),
                ("0 9 * * 6", "0 0 9 * * 7"),
                ("0 9 * * MON", "0 0 9 * * 2"),
                ("0 9 * * sun", "0 0 9 * * 1"),
                ("0 9 * * MON-FRI", "0 0 9 * * 2,3,4,5,6"),
                ("0 9 * * 1-5", "0 0 9 * * 2,3,4,5,6"),
                ("0 9 * * 5-7", "0 0 9 * * 1,6,7"),
                ("0 9 * * FRI-SUN", "0 0 9 * * 1,6,7"),
                ("0 9 * * 0,6", "0 0 9 * * 1,7"),
                ("0 9 * * 0-7", "0 0 9 * * *"),
                ("0 9 * * */2", "0 0 9 * * 1,3,5,7"),
                ("0 9 * * 1-5/2", "0 0 9 * * 2,4,6"),
                ("*/5 * * * *", "0 */5 * * * *"),
            ];
            for (input, expected) in table {
                assert_eq!(source(input), expected, "{input}");
            }
        }

        #[test]
        fn rejects_wrong_field_count_and_bad_weekdays() {
            assert!(schedule_source("* * * *").is_err());
            assert!(schedule_source("0 * * * * *").is_err());
            assert!(schedule_source("0 0 9 * * 1 2024").is_err());
            for bad in ["8", "-1", "MONDAY", "5-1", "1/0", "1/x", ""] {
                assert!(
                    schedule_source(&format!("0 9 * * {bad}")).is_err(),
                    "{bad:?} should be rejected"
                );
            }
        }

        #[test]
        fn monday_runs_on_monday_and_sunday_on_sunday() {
            let start = Utc
                .with_ymd_and_hms(2025, 1, 1, 0, 0, 0)
                .unwrap()
                .fixed_offset();
            for (expr, weekday) in [
                ("0 9 * * 1", Weekday::Mon),
                ("0 9 * * 0", Weekday::Sun),
                ("0 9 * * 7", Weekday::Sun),
                ("0 9 * * 6", Weekday::Sat),
            ] {
                let schedule = Schedule::from_str(&source(expr)).unwrap();
                let runs = runs_after(&schedule, &Utc, &start, 5);
                assert!(runs.iter().all(|r| r.weekday() == weekday), "{expr}");
            }
        }

        #[test]
        fn named_zone_follows_dst_but_fixed_offset_does_not() {
            let schedule = Schedule::from_str(&source("0 9 * * *")).unwrap();
            let start = Utc
                .with_ymd_and_hms(2025, 3, 28, 12, 0, 0)
                .unwrap()
                .fixed_offset();
            let berlin = runs_after(&schedule, &chrono_tz::Europe::Berlin, &start, 4);
            let offsets: Vec<i32> = berlin
                .iter()
                .map(|r| r.offset().local_minus_utc())
                .collect();
            // DST starts on 2025-03-30: 09:00 local moves from +01:00 to +02:00.
            assert_eq!(offsets, vec![3600, 7200, 7200, 7200]);
            assert!(
                berlin
                    .iter()
                    .all(|r| r.with_timezone(&chrono_tz::Europe::Berlin).hour() == 9)
            );

            let fixed = FixedOffset::east_opt(3600).unwrap();
            let runs = runs_after(&schedule, &fixed, &start, 4);
            assert!(
                runs.iter()
                    .all(|r| r.offset().local_minus_utc() == 3600 && r.hour() == 9)
            );
        }

        #[test]
        fn matches_ignores_seconds_and_evaluates_in_cron_zone() {
            let schedule = Schedule::from_str(&source("30 9 * * *")).unwrap();
            let utc = Utc
                .with_ymd_and_hms(2025, 1, 1, 9, 30, 42)
                .unwrap()
                .fixed_offset();
            assert!(includes_minute(&schedule, &Utc, &utc));
            assert!(!includes_minute(&schedule, &chrono_tz::Asia::Tokyo, &utc));
            let tokyo = Utc
                .with_ymd_and_hms(2025, 1, 1, 0, 30, 5)
                .unwrap()
                .fixed_offset();
            assert!(includes_minute(&schedule, &chrono_tz::Asia::Tokyo, &tokyo));
        }

        #[test]
        fn after_a_sub_second_instant_gives_the_next_minute() {
            let schedule = Schedule::from_str(&source("* * * * *")).unwrap();
            let start = Utc
                .with_ymd_and_hms(2025, 1, 1, 10, 0, 0)
                .unwrap()
                .with_nanosecond(200_000_000)
                .unwrap()
                .fixed_offset();
            let next = runs_after(&schedule, &Utc, &start, 1)[0];
            assert_eq!((next.hour(), next.minute()), (10, 1));
        }
    }
}

#[pymodule]
pub mod cronjob {
    use std::str::FromStr;

    use chrono::{DateTime, FixedOffset, Utc};
    use chrono_tz::Tz;
    use pyo3::{
        Bound, Py, PyAny, PyResult, Python,
        exceptions::{PyTypeError, PyValueError},
        pyclass, pymethods,
        types::PyAnyMethods,
    };

    use super::crontab;

    /// The zone cron fields are evaluated in.
    enum CronTz {
        Fixed(FixedOffset),
        Named(Tz),
    }

    impl CronTz {
        fn from_py(obj: &Bound<'_, PyAny>) -> PyResult<Self> {
            let named = |name: &str| {
                name.parse::<Tz>()
                    .map(CronTz::Named)
                    .map_err(|_| PyValueError::new_err(format!("Unknown timezone {name:?}")))
            };
            if let Ok(name) = obj.extract::<String>() {
                return named(&name);
            }
            if let Ok(offset) = obj.extract::<FixedOffset>() {
                return Ok(CronTz::Fixed(offset));
            }
            // zoneinfo.ZoneInfo exposes its IANA name as `key` (None for zones loaded from a file).
            if let Some(key) = obj.getattr_opt("key")?
                && let Ok(name) = key.extract::<String>()
            {
                return named(&name);
            }
            Err(PyTypeError::new_err(
                "timezone must be a zoneinfo.ZoneInfo, a fixed-offset tzinfo or an IANA zone name",
            ))
        }

        fn runs_after(
            &self,
            schedule: &cron::Schedule,
            after: &DateTime<FixedOffset>,
            n: usize,
        ) -> Vec<DateTime<FixedOffset>> {
            match self {
                CronTz::Fixed(offset) => crontab::runs_after(schedule, offset, after, n),
                CronTz::Named(tz) => crontab::runs_after(schedule, tz, after, n),
            }
        }

        fn includes(&self, schedule: &cron::Schedule, value: &DateTime<FixedOffset>) -> bool {
            match self {
                CronTz::Fixed(offset) => crontab::includes_minute(schedule, offset, value),
                CronTz::Named(tz) => crontab::includes_minute(schedule, tz, value),
            }
        }
    }

    /// A 5-field crontab expression evaluated in a timezone.
    ///
    /// Weekdays follow crontab: 0 and 7 are Sunday, 1 is Monday ... 6 is Saturday, or `SUN`..`SAT`.
    #[pyclass]
    struct CronExpr {
        cronexpr: cron::Schedule,
        zone: CronTz,
        py_timezone: Py<PyAny>,

        #[pyo3(get)]
        next_run: DateTime<FixedOffset>,
    }

    impl CronExpr {
        fn first_after(&self, after: &DateTime<FixedOffset>) -> Option<DateTime<FixedOffset>> {
            self.zone
                .runs_after(&self.cronexpr, after, 1)
                .into_iter()
                .next()
        }
    }

    #[pymethods]
    impl CronExpr {
        #[new]
        #[doc = "Create a new CronExpr with the given cron expression and timezone (zoneinfo.ZoneInfo, fixed-offset tzinfo or IANA name)"]
        pub fn new(expression: &str, timezone: &Bound<'_, PyAny>) -> PyResult<Self> {
            let source = crontab::schedule_source(expression)
                .map_err(|e| PyValueError::new_err(format!("Invalid cron expression: {e}")))?;
            let cronexpr = cron::Schedule::from_str(&source)
                .map_err(|e| PyValueError::new_err(format!("Invalid cron expression: {e}")))?;
            let zone = CronTz::from_py(timezone)?;

            let now = Utc::now().fixed_offset();
            let next_run = zone
                .runs_after(&cronexpr, &now, 1)
                .into_iter()
                .next()
                .ok_or_else(|| {
                    PyValueError::new_err("No upcoming runs for this cron expression")
                })?;

            Ok(Self {
                cronexpr,
                zone,
                py_timezone: timezone.clone().unbind(),
                next_run,
            })
        }

        #[getter]
        pub fn timezone(&self, py: Python<'_>) -> Py<PyAny> {
            self.py_timezone.clone_ref(py)
        }

        #[doc = "Update the next_run field to the next scheduled time"]
        pub fn update(&mut self) -> PyResult<()> {
            self.next_run = self
                .first_after(&Utc::now().fixed_offset())
                .ok_or_else(|| PyValueError::new_err("No next run scheduled"))?;
            Ok(())
        }

        #[doc = "Set next_run to the first scheduled time strictly after the given datetime"]
        pub fn update_after(&mut self, after: DateTime<FixedOffset>) -> PyResult<()> {
            self.next_run = self.first_after(&after).ok_or_else(|| {
                PyValueError::new_err("No runs scheduled after the specified datetime")
            })?;
            Ok(())
        }

        #[doc = "Check if the minute of the given datetime matches this cron expression (seconds are ignored)"]
        pub fn matches(&self, value: DateTime<FixedOffset>) -> PyResult<bool> {
            Ok(self.zone.includes(&self.cronexpr, &value))
        }

        #[doc = "Get the next n scheduled runs"]
        pub fn upcoming_runs(&self, n: usize) -> Vec<DateTime<FixedOffset>> {
            self.zone
                .runs_after(&self.cronexpr, &Utc::now().fixed_offset(), n)
        }
    }
}
