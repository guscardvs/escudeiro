use pyo3::prelude::*;
mod url;

#[pymodule]
fn escudeiro_pyrs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    // URL module
    {
        let url_module = PyModule::new(m.py(), "url")?;
        url_module.add_class::<url::Query>()?;
        url_module.add_class::<url::Path>()?;
        url_module.add_class::<url::Fragment>()?;
        url_module.add_class::<url::Netloc>()?;
        url_module.add_class::<url::URL>()?;
        m.add_submodule(&url_module)?;
    }
    Ok(())
}
