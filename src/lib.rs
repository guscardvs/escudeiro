use pyo3::prelude::pymodule;

mod strings;
mod url;

#[pymodule]
mod escudeiro_pyrs {
    use super::*;

    #[pymodule_export]
    use strings::strings;

    #[pymodule_export]
    use super::url::url;
}
