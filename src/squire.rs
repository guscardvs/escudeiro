use pyo3::pymodule;

#[pymodule]
pub mod squire {
    use pyo3::{
        Bound, PyAny, PyResult, Python, pyfunction,
        types::{
            PyAnyMethods, PyDict, PyDictMethods, PyList, PySequence, PySet, PyString, PyTuple,
        },
    };

    #[pyfunction]
    #[pyo3(signature = (obj, by_alias = false))]
    fn make_mapping<'py>(
        py: Python<'py>,
        obj: &Bound<'py, PyAny>,
        by_alias: Option<bool>,
    ) -> PyResult<Bound<'py, PyDict>> {
        if let Ok(parser) = obj.getattr("__parse_dict__") {
            let output = parser.call1((by_alias,))?;
            return Ok(output.cast::<PyDict>()?.to_owned());
        }

        let should_alias = by_alias.unwrap_or(false);

        let sqat_ref = obj.getattr("__squire_attrs__")?;
        let squire_attrs = sqat_ref.cast::<PyDict>()?;
        let result: Bound<'py, PyDict> = PyDict::new(py);
        for (key, field) in squire_attrs {
            let str_key = key.cast::<PyString>()?;
            let alias_attr = field.getattr("alias")?;
            let field_key = if should_alias {
                alias_attr.cast::<PyString>()?
            } else {
                str_key
            };
            match obj.getattr(str_key) {
                Ok(value) => result.set_item(field_key, value)?,
                _ => (),
            };
        }
        Ok(result)
    }

    #[pyfunction]
    #[pyo3(signature = (value, by_alias = false))]
    fn deserialize<'py>(
        py: Python<'py>,
        value: &Bound<'py, PyAny>,
        by_alias: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        if let Ok(parser) = value.getattr("__parse_dict__") {
            let result = parser.call1((by_alias,))?;
            Ok(result.into())
        } else if let Ok(sequence) = value.cast::<PySequence>() {
            if sequence.is_instance_of::<PyList>() {
                let items = sequence
                    .try_iter()?
                    .map(|item| deserialize(py, &item.unwrap(), by_alias))
                    .collect::<PyResult<Vec<_>>>()?;
                Ok(PyList::new(py, items)?.cast::<PyAny>()?.to_owned())
            } else if sequence.is_instance_of::<PyTuple>() {
                let items = sequence
                    .try_iter()?
                    .map(|item| deserialize(py, &item.unwrap(), by_alias))
                    .collect::<PyResult<Vec<_>>>()?;
                Ok(PyTuple::new(py, items)?.cast::<PyAny>()?.to_owned())
            } else if sequence.is_instance_of::<PySet>() {
                let items = sequence
                    .try_iter()?
                    .map(|item| deserialize(py, &item.unwrap(), by_alias))
                    .collect::<PyResult<Vec<_>>>()?;
                Ok(PySet::new(py, items)?.cast::<PyAny>()?.to_owned())
            } else {
                Ok(sequence.cast::<PyAny>()?.to_owned())
            }
        } else if let Ok(mapping) = value.cast::<PyDict>() {
            deserialize_mapping(py, mapping, Some(by_alias))
        } else if let Ok(_) = value.getattr("__parse_dict__") {
            let mapping = make_mapping(py, value, Some(by_alias))?;
            let result = deserialize(py, &mapping, by_alias)?;
            Ok(result.into())
        } else {
            Ok(value.to_owned())
        }
    }

    #[pyfunction]
    #[pyo3(signature = (mapping, by_alias = None))]
    fn deserialize_mapping<'py>(
        py: Python<'py>,
        mapping: &Bound<'py, PyDict>,
        by_alias: Option<bool>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let result = PyDict::new(py);
        let should_alias = by_alias.unwrap_or(false);

        for (key, value) in mapping.iter() {
            let unwrapped = deserialize(py, &value, should_alias)?;
            result.set_item(key, unwrapped)?;
        }

        Ok(result.cast::<PyAny>()?.to_owned())
    }
}
