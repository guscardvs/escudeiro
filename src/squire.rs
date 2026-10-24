use pyo3::pymodule;

#[pymodule]
pub mod squire {
    use pyo3::{
        Bound, PyAny, PyResult, Python,
        exceptions::{PyRecursionError, PyValueError},
        pyfunction,
        types::{
            PyAnyMethods, PyDict, PyDictMethods, PyList, PyListMethods, PySet, PyString, PyTuple,
        },
    };

    /// Maximum container nesting `deserialize` follows before raising `RecursionError`.
    const MAX_DEPTH: usize = 500;

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
            if let Ok(value) = obj.getattr(str_key) {
                result.set_item(field_key, value)?;
            }
        }
        Ok(result)
    }

    /// Containers currently being walked (by object id), used to detect cycles.
    struct Walk {
        by_alias: bool,
        path: Vec<usize>,
    }

    impl Walk {
        /// Enter a container; fails on a cycle or when nesting is too deep.
        fn enter(&mut self, obj: &Bound<'_, PyAny>) -> PyResult<()> {
            let id = obj.as_ptr() as usize;
            if self.path.contains(&id) {
                return Err(PyValueError::new_err("circular reference detected"));
            }
            if self.path.len() >= MAX_DEPTH {
                return Err(PyRecursionError::new_err(
                    "maximum recursion depth exceeded while deserializing",
                ));
            }
            self.path.push(id);
            Ok(())
        }

        fn leave(&mut self) {
            let _ = self.path.pop();
        }

        fn items<'py>(
            &mut self,
            py: Python<'py>,
            container: &Bound<'py, PyAny>,
        ) -> PyResult<Vec<Bound<'py, PyAny>>> {
            let mut items = Vec::new();
            for item in container.try_iter()? {
                items.push(self.value(py, &item?)?);
            }
            Ok(items)
        }

        fn value<'py>(
            &mut self,
            py: Python<'py>,
            value: &Bound<'py, PyAny>,
        ) -> PyResult<Bound<'py, PyAny>> {
            if let Some(parser) = value.getattr_opt("__parse_dict__")? {
                return parser.call1((self.by_alias,));
            }
            let is_list = value.is_instance_of::<PyList>();
            let is_tuple = value.is_instance_of::<PyTuple>();
            let is_set = value.is_instance_of::<PySet>();
            let is_dict = value.is_instance_of::<PyDict>();
            if !(is_list || is_tuple || is_set || is_dict) {
                return Ok(value.to_owned());
            }

            self.enter(value)?;
            let result = if is_dict {
                self.dict(py, value.cast::<PyDict>()?)
            } else {
                self.items(py, value).and_then(|items| {
                    if is_list {
                        Ok(PyList::new(py, items)?.into_any())
                    } else if is_tuple {
                        Ok(PyTuple::new(py, items)?.into_any())
                    } else {
                        // Converted items (e.g. dicts from data classes) may be unhashable: keep them as a list.
                        match PySet::new(py, items.iter()) {
                            Ok(set) => Ok(set.into_any()),
                            Err(_) => Ok(PyList::new(py, items)?.into_any()),
                        }
                    }
                })
            };
            self.leave();
            result
        }

        fn dict<'py>(
            &mut self,
            py: Python<'py>,
            mapping: &Bound<'py, PyDict>,
        ) -> PyResult<Bound<'py, PyAny>> {
            let result = PyDict::new(py);
            // Snapshot so a mutation during a `__parse_dict__` call cannot invalidate the iterator.
            let entries = mapping.items();
            for entry in entries.iter() {
                let (key, value) = entry.extract::<(Bound<'py, PyAny>, Bound<'py, PyAny>)>()?;
                result.set_item(key, self.value(py, &value)?)?;
            }
            Ok(result.into_any())
        }
    }

    /// Recursively convert data classes, lists, tuples, sets and dicts to builtin containers.
    ///
    /// Raises `RecursionError` when nesting exceeds the limit and `ValueError` on circular references.
    /// A set whose converted items are unhashable (e.g. dicts) becomes a list.
    #[pyfunction]
    #[pyo3(signature = (value, by_alias = false))]
    fn deserialize<'py>(
        py: Python<'py>,
        value: &Bound<'py, PyAny>,
        by_alias: bool,
    ) -> PyResult<Bound<'py, PyAny>> {
        Walk {
            by_alias,
            path: Vec::new(),
        }
        .value(py, value)
    }

    #[pyfunction]
    #[pyo3(signature = (mapping, by_alias = None))]
    fn deserialize_mapping<'py>(
        py: Python<'py>,
        mapping: &Bound<'py, PyDict>,
        by_alias: Option<bool>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let mut walk = Walk {
            by_alias: by_alias.unwrap_or(false),
            path: Vec::new(),
        };
        walk.enter(mapping.as_any())?;
        let result = walk.dict(py, mapping);
        walk.leave();
        result
    }
}
