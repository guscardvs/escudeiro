use pyo3::pymodule;

#[pymodule]
pub mod filetree {
    use pyo3::{PyResult, exceptions::PyValueError, pyclass, pyfunction, pymethods};
    use std::sync::{Arc, Mutex};

    #[pyclass(eq, eq_int)]
    #[derive(PartialEq)]
    enum ErrorCodes {
        InvalidParam = 1,
        UnableToAcquireLock,
        InvalidPath,
        DuplicateFile,
    }

    #[pyfunction]
    #[pyo3(signature = (filename, private = false, dunder = false))]
    pub fn python_filename(filename: String, private: bool, dunder: bool) -> PyResult<String> {
        if private && dunder {
            Err(PyValueError::new_err((
                "Cannot have a file that is both private and dunder.",
                ErrorCodes::InvalidParam,
            )))
        } else if private {
            Ok(format!("_{}.py", filename))
        } else if dunder {
            Ok(format!("__{}__.py", filename))
        } else {
            Ok(format!("{}.py", filename))
        }
    }

    #[pyfunction]
    pub fn init_file() -> PyResult<String> {
        python_filename("init".to_string(), false, true)
    }

    // Internal node representation using Arc<Mutex<>> for interior mutability
    type NodeRef = Arc<Mutex<FsNodeInternal>>;

    struct FsNodeInternal {
        name: String,
        children: Vec<NodeRef>,
        content: Option<Vec<u8>>,
    }

    impl FsNodeInternal {
        fn new(name: String, content: Option<Vec<u8>>) -> Self {
            Self {
                name,
                children: Vec::new(),
                content,
            }
        }

        fn is_file(&self) -> bool {
            self.content.is_some()
        }

        fn contains_shallow(&self, name: &str) -> bool {
            self.children.iter().any(|node| {
                if let Ok(node) = node.lock() {
                    node.name == name
                } else {
                    false
                }
            })
        }

        fn get_shallow(&self, name: &str) -> Option<NodeRef> {
            self.children
                .iter()
                .find(|node| {
                    if let Ok(node) = node.lock() {
                        node.name == name
                    } else {
                        false
                    }
                })
                .cloned()
        }

        fn append_content(&mut self, content: &mut Vec<u8>) {
            match &mut self.content {
                Some(curcontent) => curcontent.append(content),
                None => self.content = Some(content.to_vec()),
            }
        }
    }

    // Python-exposed node wrapper
    #[pyclass]
    #[derive(Clone)]
    pub struct FsNode {
        inner: NodeRef,
    }

    #[pymethods]
    impl FsNode {
        #[new]
        #[pyo3(signature = (name, content = None))]
        pub fn new(name: String, content: Option<Vec<u8>>) -> Self {
            let node = FsNodeInternal::new(name, content);
            Self {
                inner: Arc::new(Mutex::new(node)),
            }
        }

        #[getter]
        pub fn name(&self) -> PyResult<String> {
            match self.inner.lock() {
                Ok(node) => Ok(node.name.clone()),
                Err(_) => Err(PyValueError::new_err((
                    "Failed to acquire lock on node",
                    ErrorCodes::UnableToAcquireLock,
                ))),
            }
        }

        #[getter]
        pub fn content(&self) -> PyResult<Option<Vec<u8>>> {
            match self.inner.lock() {
                Ok(node) => Ok(node.content.clone()),
                Err(_) => Err(PyValueError::new_err((
                    "Failed to acquire lock on node",
                    ErrorCodes::UnableToAcquireLock,
                ))),
            }
        }

        #[getter]
        pub fn children(&self) -> PyResult<Vec<FsNode>> {
            match self.inner.lock() {
                Ok(node) => {
                    let children = node
                        .children
                        .iter()
                        .map(|child| FsNode {
                            inner: child.clone(),
                        })
                        .collect();
                    Ok(children)
                }
                Err(_) => Err(PyValueError::new_err((
                    "Failed to acquire lock on node",
                    ErrorCodes::UnableToAcquireLock,
                ))),
            }
        }

        pub fn is_file(&self) -> PyResult<bool> {
            match self.inner.lock() {
                Ok(node) => Ok(node.is_file()),
                Err(_) => Err(PyValueError::new_err((
                    "Failed to acquire lock on node",
                    ErrorCodes::UnableToAcquireLock,
                ))),
            }
        }

        pub fn contains_shallow(&self, name: String) -> PyResult<bool> {
            match self.inner.lock() {
                Ok(node) => Ok(node.contains_shallow(&name)),
                Err(_) => Err(PyValueError::new_err((
                    "Failed to acquire lock on node",
                    ErrorCodes::UnableToAcquireLock,
                ))),
            }
        }

        pub fn get_shallow(&self, name: String) -> PyResult<Option<FsNode>> {
            match self.inner.lock() {
                Ok(node) => {
                    let child = node
                        .get_shallow(&name)
                        .map(|node_ref| FsNode { inner: node_ref });
                    Ok(child)
                }
                Err(_) => Err(PyValueError::new_err((
                    "Failed to acquire lock on node",
                    ErrorCodes::UnableToAcquireLock,
                ))),
            }
        }

        pub fn add_child(&self, node: &FsNode) -> PyResult<()> {
            match self.inner.lock() {
                Ok(mut self_node) => {
                    if self_node.is_file() {
                        Err(PyValueError::new_err((
                            "Cannot add children to a file",
                            ErrorCodes::InvalidPath,
                        )))
                    } else {
                        self_node.children.push(node.inner.clone());
                        Ok(())
                    }
                }
                Err(_) => Err(PyValueError::new_err((
                    "Failed to acquire lock on node",
                    ErrorCodes::UnableToAcquireLock,
                ))),
            }
        }
        fn write_content(&self, content: Vec<u8>) -> PyResult<()> {
            match self.inner.lock() {
                Ok(mut self_node) => {
                    if self_node.children.len() > 0 {
                        return Err(PyValueError::new_err((
                            format!(
                                "Trying to write into file {} where there is a folder",
                                self_node.name
                            ),
                            ErrorCodes::InvalidPath,
                        )));
                    } else {
                        self_node.content = Some(content);
                        Ok(())
                    }
                }
                Err(_) => Err(PyValueError::new_err((
                    "Failed to acquire lock on node",
                    ErrorCodes::UnableToAcquireLock,
                ))),
            }
        }

        fn append_content(&self, other: Vec<u8>) -> PyResult<()> {
            match self.inner.lock() {
                Ok(mut self_node) => {
                    if self_node.children.len() > 0 {
                        return Err(PyValueError::new_err((
                            format!(
                                "Trying to write into file {} where there is a folder",
                                self_node.name
                            ),
                            ErrorCodes::InvalidPath,
                        )));
                    } else {
                        self_node.append_content(&mut other.clone());
                        Ok(())
                    }
                }
                Err(_) => Err(PyValueError::new_err((
                    "Failed to acquire lock on node",
                    ErrorCodes::UnableToAcquireLock,
                ))),
            }
        }
    }

    #[pyclass]
    pub struct FsTree {
        root: FsNode,
    }

    #[pymethods]
    impl FsTree {
        #[new]
        pub fn new(basename: String) -> Self {
            let root = FsNode::new(basename, None);
            Self { root }
        }

        #[staticmethod]
        pub fn from_node(root: FsNode) -> Self {
            Self { root }
        }

        #[getter]
        pub fn root(&self) -> FsNode {
            self.root.clone()
        }

        #[pyo3(signature = (name, *path))]
        pub fn create_dir(&self, name: String, path: Vec<String>) -> PyResult<FsNode> {
            let target = self.navigate_path(path)?;

            // Check if directory already exists
            if let Some(existing) = target.get_shallow(name.clone())? {
                if existing.is_file()? {
                    return Err(PyValueError::new_err((
                        format!("Directory name conflicts with file {}", name),
                        ErrorCodes::InvalidPath,
                    )));
                }
                return Ok(existing);
            }

            // Create new directory node
            let new_dir = FsNode::new(name, None);
            target.add_child(&new_dir)?;

            Ok(new_dir)
        }

        #[pyo3(signature = (name, content, *path))]
        pub fn create_file(
            &self,
            name: String,
            content: Vec<u8>,
            path: Vec<String>,
        ) -> PyResult<FsNode> {
            let target = self.navigate_path(path)?;

            // Check if file already exists
            if target.contains_shallow(name.clone())? {
                return Err(PyValueError::new_err((
                    format!("File name '{}' already exists in this directory", name),
                    ErrorCodes::DuplicateFile,
                )));
            }

            // Create new file node
            let new_file = FsNode::new(name, Some(content));
            target.add_child(&new_file)?;

            Ok(new_file)
        }

        #[pyo3(signature = (*path))]
        pub fn get_node(&self, path: Vec<String>) -> PyResult<FsNode> {
            self.navigate_path(path)
        }

        // Helper method to navigate to a path
        fn navigate_path(&self, path: Vec<String>) -> PyResult<FsNode> {
            let mut current = self.root.clone();

            for component in path {
                if let Some(child) = current.get_shallow(component.clone())? {
                    if child.is_file()? {
                        return Err(PyValueError::new_err((
                            format!("Path component '{}' is a file, not a directory", component),
                            ErrorCodes::InvalidPath,
                        )));
                    }
                    current = child;
                } else {
                    // Create intermediate directory if it doesn't exist
                    let new_dir = FsNode::new(component.clone(), None);
                    current.add_child(&new_dir)?;
                    current = new_dir;
                }
            }

            Ok(current)
        }
    }
}
