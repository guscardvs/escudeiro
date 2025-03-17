use pyo3::prelude::*;
mod strings;
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
    // Strings module
    {
        let strings_module = PyModule::new(m.py(), "strings")?;
        strings_module.add_function(wrap_pyfunction!(strings::replace_all, m)?)?;
        strings_module.add_function(wrap_pyfunction!(strings::replace_by, m)?)?;
        strings_module.add_function(wrap_pyfunction!(strings::to_snake, m)?)?;
        strings_module.add_function(wrap_pyfunction!(strings::to_camel, m)?)?;
        strings_module.add_function(wrap_pyfunction!(strings::to_pascal, m)?)?;
        strings_module.add_function(wrap_pyfunction!(strings::to_kebab, m)?)?;
        strings_module.add_function(wrap_pyfunction!(strings::squote, m)?)?;
        strings_module.add_function(wrap_pyfunction!(strings::dquote, m)?)?;
        strings_module.add_function(wrap_pyfunction!(strings::sentence, m)?)?;
        strings_module.add_function(wrap_pyfunction!(strings::exclamation, m)?)?;
        strings_module.add_function(wrap_pyfunction!(strings::question, m)?)?;
        m.add_submodule(&strings_module)?;
    }
    Ok(())
}
