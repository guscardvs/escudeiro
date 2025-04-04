use pyo3::pymodule;

#[pymodule]
pub mod filetree {
    use core::fmt;
    use pyo3::{PyResult, exceptions::PyValueError, pyclass, pyfunction, pymethods};
    use std::result::Result;

    #[pyfunction]
    #[pyo3(signature = (filename, private = false, dunder = false))]
    pub fn python_filename(filename: String, private: bool, dunder: bool) -> PyResult<String> {
        if private && dunder {
            Err(PyValueError::new_err(
                "Cannot have a file that is both private and dunder.",
            ))
        } else if private {
            Ok(format!("_{}.py", filename))
        } else {
            Ok(format!("__{}__.py", filename))
        }
    }

    #[pyfunction]
    pub fn init_file() -> PyResult<String> {
        python_filename("init".to_string(), false, true)
    }

    #[derive(Debug, Clone)]
    pub struct InvalidValueError;

    impl fmt::Display for InvalidValueError {
        fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
            write!(f, "invalid operation for value used.")
        }
    }

    #[pyclass]
    #[derive(Clone)]
    pub struct FsNode {
        #[pyo3(get)]
        name: String,
        children: Vec<FsNode>,
        #[pyo3(get)]
        content: Option<Vec<u8>>,
    }

    #[pymethods]
    impl FsNode {
        #[new]
        #[pyo3(signature = (name, content = None))]
        pub fn new(name: String, content: Option<Vec<u8>>) -> Self {
            Self {
                name,
                children: Vec::<FsNode>::new(),
                content,
            }
        }

        pub fn is_file(&self) -> bool {
            self.content.is_none()
        }
    }

    impl FsNode {
        pub fn add_children(&mut self, children: Vec<FsNode>) -> Result<(), InvalidValueError> {
            if self.is_file() {
                Err(InvalidValueError)
            } else {
                self.children.extend(children);
                Ok(())
            }
        }
    }

    #[pyclass]
    pub struct FsTree {
        #[pyo3(get)]
        root: FsNode,
    }

    #[pymethods]
    impl FsTree {
        #[new]
        pub fn new(basename: String) -> Self {
            let root = FsNode::new(basename, None);
            Self { root }
        }

        pub fn create_dir(name: String, path: Vec<String>) -> Self {}
    }
}
