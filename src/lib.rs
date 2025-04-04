use pyo3::prelude::pymodule;

mod cronjob;
mod filetree;
mod squire;
mod strings;
mod url;

#[pymodule]
mod escudeiro_pyrs {
    use super::*;

    #[pymodule_export]
    use strings::strings;

    #[pymodule_export]
    use super::url::url;

    #[pymodule_export]
    use squire::squire;

    #[pymodule_export]
    use cronjob::cronjob;

    #[pymodule_export]
    use filetree::filetree;
}
