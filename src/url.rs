use pyo3::pymodule;

#[pymodule]
pub mod url {
    use once_cell::sync::Lazy;
    use pyo3::PyResult;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::{pyclass, pymethods};
    use regex::Regex;
    use std::collections::{BTreeMap, HashMap};
    use std::ops::Not;
    use url::ParseError;
    use url::{Url, form_urlencoded::byte_serialize};

    #[pyclass]
    #[derive(Clone)]
    pub struct Query {
        #[pyo3(get)]
        params: BTreeMap<String, Vec<String>>,
    }

    static _ARBITRARY_URL: &str = "https://example.com";

    #[pymethods]
    impl Query {
        #[new]
        pub fn new(querystr: &str) -> Self {
            let full_url = format!("{_ARBITRARY_URL}/?{}", querystr);
            let params = BTreeMap::new();
            let mut instance = Self { params };
            match Url::parse(full_url.as_str()) {
                Ok(url) => {
                    let key_pairs = url.query_pairs().into_owned();

                    for (key, value) in key_pairs {
                        instance.add(key, value);
                    }
                    instance
                }
                Err(_) => instance,
            }
        }

        pub fn add(&mut self, key: String, value: String) {
            self.params
                .entry(key.clone())
                .or_insert_with(Vec::new)
                .push(value.clone());
        }

        pub fn set(&mut self, key: String, value: String) {
            self.params
                .entry(key.clone())
                .or_insert_with(Vec::new)
                .clear();
            self.params
                .entry(key.clone())
                .and_modify(|vec| vec.push(value));
        }

        pub fn get(&self) -> BTreeMap<String, Vec<String>> {
            self.params.clone()
        }

        pub fn encode(&self) -> String {
            let mut parts = Vec::with_capacity(self.params.iter().map(|(_, v)| v.len()).sum());
            for (key, values) in self.params.iter() {
                let urlencoded_key: String = byte_serialize(key.as_bytes()).collect();
                for value in values.iter() {
                    let urlencoded_value: String = byte_serialize(value.as_bytes()).collect();
                    parts.push(format!("{urlencoded_key}={urlencoded_value}"));
                }
            }
            parts.join("&")
        }

        pub fn add_map(&mut self, map: HashMap<String, String>) {
            for (key, value) in map {
                self.add(key, value);
            }
        }

        pub fn set_map(&mut self, map: HashMap<String, String>) {
            self.params.clear();
            for (key, value) in map {
                self.params.insert(key, Vec::from(vec![value]));
            }
        }

        pub fn remove(&mut self, key: String) {
            self.params.remove(&key);
        }

        pub fn copy(&self) -> Self {
            self.clone()
        }

        pub fn omit_empty_equal(&self) -> String {
            let mut parts = Vec::with_capacity(self.params.iter().map(|(_, v)| v.len()).sum());
            for (key, values) in self.params.iter() {
                let urlencoded_key: String = byte_serialize(key.as_bytes()).collect();
                for value in values.iter() {
                    if value.is_empty() {
                        parts.push(urlencoded_key.clone());
                    } else {
                        let urlencoded_value: String = byte_serialize(value.as_bytes()).collect();
                        parts.push(format!("{}={}", urlencoded_key, urlencoded_value));
                    }
                }
            }
            parts.join("&")
        }

        pub fn first(&self) -> HashMap<String, String> {
            let mut params = HashMap::<String, String>::with_capacity(self.params.len());
            for (key, values) in self.params.iter() {
                if let Some(first_value) = values.first() {
                    params.insert(key.into(), first_value.into());
                }
            }
            params
        }

        pub fn compare(&self, other: Self) -> bool {
            self.params == other.params
        }
    }

    #[pyclass]
    #[derive(Clone)]
    pub struct Path {
        #[pyo3(get)]
        segments: Vec<String>,
    }

    #[pymethods]
    impl Path {
        #[new]
        pub fn new(pathstr: &str) -> Self {
            let mut segments = Vec::<String>::with_capacity(pathstr.matches('/').count());
            append_segments(&mut segments, pathstr);
            Self { segments }
        }

        pub fn add(&mut self, pathstr: &str) {
            append_segments(&mut self.segments, pathstr);
        }

        pub fn add_path(&mut self, pathobj: std::path::PathBuf) -> PyResult<()> {
            if let Some(pathstr) = pathobj.to_str() {
                self.add(pathstr);
                Ok(())
            } else {
                Err(PyValueError::new_err(
                    "Path contains invalid unicode characters.",
                ))
            }
        }

        pub fn clear(&mut self) {
            self.segments.clear();
        }

        pub fn is_dir(&self) -> bool {
            self.segments.is_empty() || self.segments.last().map_or(true, |last| last.is_empty())
        }

        pub fn encode(&self) -> String {
            DUPLICATES_REGEX
                .replace(self.segments.join("/").as_str(), "/")
                .to_string()
        }

        pub fn normalize(&mut self) {
            if self.segments.is_empty() {
                return;
            }
            let encoded = self.encode();
            self.clear();
            self.add(normalize(encoded.as_str()).as_str());
        }

        pub fn copy(&self) -> Self {
            self.clone()
        }

        pub fn get(&self) -> Vec<String> {
            self.segments.clone()
        }

        pub fn compare(&self, other: Self) -> bool {
            self.segments == other.segments
        }
    }

    pub fn append_segments(source: &mut Vec<String>, extrapath: &str) {
        if extrapath.len() == 0 {
            return;
        }
        if let Some(last) = source.last() {
            if last == "" {
                source.pop();
            }
        }
        let formatted_path = extrapath.trim_start_matches("/");
        let full_url = format!("{_ARBITRARY_URL}/{formatted_path}");
        let initial_len = source.len();
        match Url::parse(full_url.as_str()) {
            Ok(url) => {
                for part in url.path().trim_end_matches("/").split("/") {
                    if part != "" || initial_len == 0 {
                        source.push(part.to_string());
                    }
                }
            }
            Err(_) => {}
        }
        if extrapath.ends_with("/") {
            source.push("".to_string())
        }
    }

    static DUPLICATES_REGEX: Lazy<Regex> = Lazy::new(|| Regex::new("/+").unwrap());

    pub fn normalize(path: &str) -> String {
        let dedup = DUPLICATES_REGEX.replace(path, "/");
        let mut stack = Vec::<&str>::new();
        for segment in dedup.split('/') {
            match segment {
                ".." if !stack.is_empty() => {
                    stack.pop();
                }
                "." | "" => continue,
                _ => stack.push(segment),
            }
        }
        let normalized = format!("/{}", stack.join("/"));
        if path.ends_with('/') {
            normalized + "/"
        } else {
            normalized
        }
    }

    const PERCENT_REGEX: &str = r"%[a-fA-F\d][a-fA-F\d]";

    static IS_VALID_ENCODED_PATH: Lazy<Regex> = Lazy::new(|| {
        let allowed_chars = r"\-\.\~\:\@\!\$\&\'\(\)\*\+\,\;\=";
        let pattern = format!(r"^([\w{}]|({}))*$", allowed_chars, PERCENT_REGEX);
        Regex::new(&pattern).unwrap()
    });

    #[pyclass]
    #[derive(Clone)]
    pub struct Fragment {
        fragment: String,
    }

    #[pymethods]
    impl Fragment {
        #[new]
        pub fn new(fragmentstr: &str) -> Self {
            Self {
                fragment: if !IS_VALID_ENCODED_PATH.is_match(fragmentstr) {
                    byte_serialize(fragmentstr.as_bytes()).collect::<String>()
                } else {
                    fragmentstr.to_string()
                },
            }
        }

        pub fn encode(&self) -> &str {
            self.fragment.as_str()
        }

        pub fn set(&mut self, fragmentstr: &str) {
            self.fragment = byte_serialize(fragmentstr.as_bytes()).collect::<String>();
        }

        pub fn copy(&self) -> Self {
            self.clone()
        }

        pub fn compare(&self, other: Self) -> bool {
            self.fragment == other.fragment
        }
    }

    #[pyclass]
    #[derive(Clone)]
    pub struct Netloc {
        #[pyo3(get)]
        username: Option<String>,
        #[pyo3(get)]
        password: Option<String>,
        #[pyo3(get)]
        host: String,
        port: Option<u16>,
    }

    impl Netloc {
        fn parse_url(&mut self, url: &Url) {
            self.username = url
                .username()
                .is_empty()
                .not()
                .then(|| url.username().to_string());
            self.password = url.password().map(String::from);
            self.host = url.host_str().unwrap_or("").to_string();
            self.port = url.port();
        }
    }

    #[pymethods]
    impl Netloc {
        #[new]
        pub fn new(netloc: &str) -> PyResult<Self> {
            let mut instance = Self {
                username: None,
                password: None,
                host: "".to_string(),
                port: None,
            };
            instance.parse(netloc)?;
            Ok(instance)
        }

        pub fn encode(&self) -> String {
            let mut netloc = String::new();
            if let Some(username) = &self.username {
                let encoded = byte_serialize(username.as_bytes()).collect::<String>();
                netloc.push_str(encoded.as_str());

                if let Some(password) = &self.password {
                    let encoded = byte_serialize(password.as_bytes()).collect::<String>();
                    netloc.push_str(format!(":{encoded}").as_str());
                }
                netloc.push('@');
            }
            netloc.push_str(self.host.as_str());

            if let Some(port) = &self.port {
                netloc.push_str(format!(":{port}").as_str())
            }

            netloc
        }

        pub fn parse(&mut self, netloc: &str) -> PyResult<()> {
            let full_url = format!("https://{netloc}");
            match Url::parse(full_url.as_str()) {
                Ok(url) => {
                    self.parse_url(&url);
                    Ok(())
                }
                Err(ParseError::InvalidPort) => Err(PyValueError::new_err(
                    "Invalid port received while parsing netloc.",
                )),
                Err(_) => Ok(()),
            }
        }

        #[pyo3(signature = (host = None, port = None, username = None, password = None))]
        pub fn set(
            &mut self,
            host: Option<&str>,
            port: Option<u16>,
            username: Option<&str>,
            password: Option<&str>,
        ) {
            self.host = host.map_or(self.host.clone(), |hoststr| {
                if !hoststr.is_empty() {
                    hoststr.to_string()
                } else {
                    self.host.clone()
                }
            });
            self.port = port.map_or(self.port, |val| Some(val));
            self.username =
                username.map_or(self.username.clone(), |username| Some(username.to_string()));
            self.password =
                password.map_or(self.password.clone(), |password| Some(password.to_string()));
        }

        pub fn merge(&self, other: Self) -> Self {
            Self {
                host: if !other.host.is_empty() {
                    other.host
                } else {
                    self.host.clone()
                },
                port: other.port.or(self.port),
                username: other.username.or_else(|| self.username.clone()),
                password: other.password.or_else(|| self.password.clone()),
            }
        }

        pub fn merge_left(&self, other: Self) -> Self {
            Self {
                host: if !self.host.is_empty() {
                    self.host.clone()
                } else {
                    other.host
                },
                port: self.port.map_or(other.port, |val| Some(val)),
                username: self.username.clone().or_else(|| other.username.clone()),
                password: self.password.clone().or_else(|| other.password.clone()),
            }
        }

        pub fn merge_inplace(&mut self, other: Self) {
            self.host = if !other.host.is_empty() {
                other.host
            } else {
                self.host.clone()
            };
            self.port = other.port.map_or(self.port, |val| Some(val));
            if other.username.is_some() {
                self.username = other.username;
            }
            if other.password.is_some() {
                self.password = other.password;
            }
        }

        #[staticmethod]
        #[pyo3(signature = (host, port = None, username = None, password = None))]
        pub fn from_args(
            host: &str,
            port: Option<u16>,
            username: Option<&str>,
            password: Option<&str>,
        ) -> Self {
            Self {
                host: host.to_string(),
                port,
                username: username.map(String::from),
                password: password.map(String::from),
            }
        }

        pub fn copy(&self) -> Self {
            self.clone()
        }

        #[getter]
        pub fn get_port(&self) -> Option<u16> {
            self.port
        }

        #[setter]
        pub fn set_port(&mut self, number: isize) -> PyResult<()> {
            if number < 0 || number > std::u16::MAX as isize {
                Err(PyValueError::new_err("Received invalid port value."))
            } else {
                self.port = Some(number as u16);
                Ok(())
            }
        }
        pub fn compare(&self, other: Self) -> bool {
            self.username == other.username
                && self.password == other.password
                && self.host == other.host
                && self.port == other.port
        }
    }

    #[pyclass]
    #[derive(Clone)]
    pub struct URL {
        #[pyo3(get, set)]
        pub scheme: String,
        #[pyo3(get, set)]
        pub netloc: Netloc,
        #[pyo3(get, set)]
        pub path: Path,
        #[pyo3(get, set)]
        pub query: Query,
        #[pyo3(get, set)]
        pub fragment: Fragment,
    }

    #[pymethods]
    impl URL {
        #[new]
        pub fn new(val: &str) -> Self {
            let mut instance = Self {
                scheme: "".to_string(),
                netloc: Netloc::from_args("", None, None, None),
                path: Path {
                    segments: Vec::<_>::new(),
                },
                query: Query {
                    params: BTreeMap::<_, _>::new(),
                },
                fragment: Fragment {
                    fragment: String::new(),
                },
            };

            match Url::parse(val) {
                Ok(url) => {
                    for (key, value) in url.query_pairs().into_owned() {
                        instance.query.add(key, value);
                    }
                    append_segments(&mut instance.path.segments, url.path());
                    instance.netloc.parse_url(&url);
                    instance.fragment.set(url.fragment().unwrap_or(""));
                    instance.scheme = url.scheme().to_string();
                    instance
                }
                Err(_) => instance,
            }
        }

        #[pyo3(signature = (append_empty_equal = true))]
        pub fn encode(&self, append_empty_equal: bool) -> String {
            let mut url = self.netloc.encode();

            if self.scheme.len() > 0 {
                url = format!("{scheme}://{url}", scheme = self.scheme)
            }

            let path_encoded = self.path.encode();
            if path_encoded.len() > 0 {
                url.push_str(path_encoded.as_str());
            }

            let resolved_query = if append_empty_equal {
                self.query.encode()
            } else {
                self.query.omit_empty_equal()
            };
            if resolved_query.len() > 0 {
                url = format!("{url}?{resolved_query}");
            }

            let fragment_encoded = self.fragment.encode();
            if fragment_encoded.len() > 0 {
                format!("{url}#{fragment}", fragment = self.fragment.encode())
            } else {
                url
            }
        }

        #[pyo3(signature = (path = None, query = None, fragment = None, netloc = None, netloc_obj = None, scheme = None))]
        pub fn add(
            &mut self,
            path: Option<&str>,
            query: Option<HashMap<String, String>>,
            fragment: Option<&str>,
            netloc: Option<&str>,
            netloc_obj: Option<Netloc>,
            scheme: Option<&str>,
        ) {
            if let Some(path) = path {
                self.path.add(path);
            }

            if let Some(query) = query {
                self.query.add_map(query);
            }

            if let Some(fragment) = fragment {
                self.fragment.set(fragment);
            }

            if let Some(netloc) = netloc {
                _ = self.netloc.parse(netloc);
            }

            if let Some(netloc_obj) = netloc_obj {
                self.netloc.merge_inplace(netloc_obj);
            }

            if let Some(scheme) = scheme {
                self.scheme = scheme.to_string();
            }
        }

        #[pyo3(signature = (path = None, query = None, fragment = None, netloc = None, netloc_obj = None, scheme = None))]
        pub fn set(
            &mut self,
            path: Option<&str>,
            query: Option<HashMap<String, String>>,
            fragment: Option<&str>,
            netloc: Option<&str>,
            netloc_obj: Option<Netloc>,
            scheme: Option<&str>,
        ) {
            if let Some(path) = path {
                self.path.clear();
                self.path.add(path);
            }

            if let Some(query) = query {
                self.query.set_map(query);
            }

            if let Some(fragment) = fragment {
                self.fragment.set(fragment);
            }

            if let Some(netloc) = netloc {
                if let Ok(netloc_instance) = Netloc::new(netloc) {
                    self.netloc = netloc_instance
                }
            }

            if let Some(netloc_obj) = netloc_obj {
                self.netloc = netloc_obj;
            }

            if let Some(scheme) = scheme {
                self.scheme = scheme.to_string();
            }
        }

        pub fn copy(&self) -> Self {
            self.clone()
        }

        #[staticmethod]
        #[pyo3(signature = (netloc = None, username = None, password  = None, host = None, port = None))]
        pub fn from_netloc(
            netloc: Option<Netloc>,
            username: Option<&str>,
            password: Option<&str>,
            host: Option<&str>,
            port: Option<u16>,
        ) -> Self {
            let mut netloc_instance =
                Netloc::from_args(host.unwrap_or(""), port, username, password);
            if let Some(netloc) = netloc {
                netloc_instance = netloc_instance.merge_left(netloc);
            }
            Self::new(netloc_instance.encode().as_str())
        }

        #[staticmethod]
        #[pyo3(signature = (path = None, query = None, fragment = None, netloc = None, netloc_obj = None, scheme = None))]
        pub fn from_args(
            path: Option<&str>,
            query: Option<HashMap<String, String>>,
            fragment: Option<&str>,
            netloc: Option<&str>,
            netloc_obj: Option<Netloc>,
            scheme: Option<&str>,
        ) -> Self {
            let mut url = Self::new("");
            url.set(path, query, fragment, netloc, netloc_obj, scheme);
            url
        }
        pub fn compare(&self, other: Self) -> bool {
            self.scheme == other.scheme
                && self.query.compare(other.query)
                && self.path.compare(other.path)
                && self.netloc.compare(other.netloc)
                && self.fragment.compare(other.fragment)
        }
    }
}
