use pyo3::pymodule;

#[pymodule]
pub mod cronjob {
    use std::str::FromStr;

    use pyo3::{PyResult, exceptions::PyValueError, pyclass, pymethods};

    #[pyclass]
    struct CronExpr {
        cronexpr: cron::Schedule,

        #[pyo3(get)]
        timezone: chrono::FixedOffset,

        #[pyo3(get)]
        next_run: chrono::DateTime<chrono::FixedOffset>,
    }

    #[pymethods]
    impl CronExpr {
        #[new]
        #[doc = "Create a new CronExpr with the given cron expression and timezone"]
        pub fn new(expression: String, timezone: chrono::FixedOffset) -> PyResult<Self> {
            let cronexpr = cron::Schedule::from_str(&format!("0 {}", expression)).map_err(|e| {
                return PyValueError::new_err(format!("Invalid cron expression: {}", e));
            })?;

            let next_run = cronexpr.upcoming(timezone).next().ok_or_else(|| {
                PyValueError::new_err("No upcoming runs for this cron expression")
            })?;

            Ok(Self {
                cronexpr,
                timezone,
                next_run,
            })
        }

        #[doc = "Update the next_run field to the next scheduled time"]
        pub fn update(&mut self) -> PyResult<()> {
            self.next_run = self
                .cronexpr
                .upcoming(self.timezone)
                .next()
                .ok_or_else(|| PyValueError::new_err("No next run scheduled"))?;
            Ok(())
        }

        pub fn update_after(
            &mut self,
            after: chrono::DateTime<chrono::FixedOffset>,
        ) -> PyResult<()> {
            self.next_run = self
                .cronexpr
                .after::<chrono::FixedOffset>(&after)
                .next()
                .ok_or_else(|| {
                    PyValueError::new_err("No runs scheduled after the specified datetime")
                })?;

            Ok(())
        }

        #[doc = "Check if the given datetime matches this cron expression"]
        pub fn matches(&self, value: chrono::DateTime<chrono::FixedOffset>) -> PyResult<bool> {
            Ok(self.cronexpr.includes(value))
        }
        #[doc = "Get the next n scheduled runs"]
        pub fn upcoming_runs(&self, n: usize) -> Vec<chrono::DateTime<chrono::FixedOffset>> {
            self.cronexpr.upcoming(self.timezone).take(n).collect()
        }
    }
}
