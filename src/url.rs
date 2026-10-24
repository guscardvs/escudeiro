use pyo3::pymodule;

#[pymodule]
pub mod url {
    use once_cell::sync::Lazy;
    use pyo3::exceptions::PyValueError;
    use pyo3::prelude::*;
    use pyo3::types::{PyDict, PyMapping};
    use regex::Regex;
    use url::form_urlencoded;
    use url::{Url, form_urlencoded::byte_serialize};

    static DUPLICATES_REGEX: Lazy<Regex> = Lazy::new(|| Regex::new("/+").unwrap());

    /// Characters kept as-is by every component besides ASCII alphanumerics.
    const BASE_ALLOWED: &str = "-._~!$&'()*+,;=";
    const PATH_ALLOWED: &str = ":@";
    const FRAGMENT_ALLOWED: &str = ":@/?";
    const USERINFO_ALLOWED: &str = "";

    /// Percent-encodes `input` for one URL component, exactly once: valid `%XX`
    /// escapes already present are kept, everything else outside the allowed set
    /// is escaped.
    fn encode_component(input: &str, extra_allowed: &str) -> String {
        let bytes = input.as_bytes();
        let mut out = String::with_capacity(input.len());
        let mut i = 0;
        while i < bytes.len() {
            let byte = bytes[i];
            if byte == b'%'
                && i + 2 < bytes.len()
                && bytes[i + 1].is_ascii_hexdigit()
                && bytes[i + 2].is_ascii_hexdigit()
            {
                out.push_str(&input[i..i + 3]);
                i += 3;
                continue;
            }
            let ch = byte as char;
            if byte.is_ascii_alphanumeric()
                || BASE_ALLOWED.contains(ch)
                || extra_allowed.contains(ch)
            {
                out.push(ch);
            } else {
                out.push_str(&format!("%{byte:02X}"));
            }
            i += 1;
        }
        out
    }

    fn mapping_pairs(map: &Bound<'_, PyMapping>) -> PyResult<Vec<(String, String)>> {
        map.items()?.extract()
    }

    #[pyclass]
    #[derive(Clone)]
    pub struct Query {
        params: Vec<(String, Vec<String>)>,
    }

    impl Query {
        fn entry(&mut self, key: &str) -> Option<&mut Vec<String>> {
            self.params
                .iter_mut()
                .find(|(existing, _)| existing == key)
                .map(|(_, values)| values)
        }

        fn sorted(&self) -> Vec<&(String, Vec<String>)> {
            let mut sorted: Vec<_> = self.params.iter().collect();
            sorted.sort_by(|a, b| a.0.cmp(&b.0));
            sorted
        }
    }

    #[pymethods]
    impl Query {
        #[new]
        pub fn new(querystr: &str) -> Self {
            let mut instance = Self { params: Vec::new() };
            for (key, value) in form_urlencoded::parse(querystr.as_bytes()).into_owned() {
                instance.add(key, value);
            }
            instance
        }

        pub fn add(&mut self, key: String, value: String) {
            match self.entry(&key) {
                Some(values) => values.push(value),
                None => self.params.push((key, vec![value])),
            }
        }

        pub fn set(&mut self, key: String, value: String) {
            match self.entry(&key) {
                Some(values) => *values = vec![value],
                None => self.params.push((key, vec![value])),
            }
        }

        pub fn get<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
            let dict = PyDict::new(py);
            for (key, values) in self.params.iter() {
                dict.set_item(key, values)?;
            }
            Ok(dict)
        }

        #[getter]
        pub fn params<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
            self.get(py)
        }

        pub fn encode(&self) -> String {
            self.encode_with(false)
        }

        pub fn add_map(&mut self, map: &Bound<'_, PyMapping>) -> PyResult<()> {
            for (key, value) in mapping_pairs(map)? {
                self.add(key, value);
            }
            Ok(())
        }

        pub fn set_map(&mut self, map: &Bound<'_, PyMapping>) -> PyResult<()> {
            let pairs = mapping_pairs(map)?;
            self.params.clear();
            for (key, value) in pairs {
                self.set(key, value);
            }
            Ok(())
        }

        pub fn remove(&mut self, key: String) {
            self.params.retain(|(existing, _)| *existing != key);
        }

        /// Sorts the parameters by key; values of one key keep their order.
        pub fn sort(&mut self) {
            self.params.sort_by(|a, b| a.0.cmp(&b.0));
        }

        pub fn copy(&self) -> Self {
            self.clone()
        }

        pub fn omit_empty_equal(&self) -> String {
            self.encode_with(true)
        }

        pub fn first<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
            let dict = PyDict::new(py);
            for (key, values) in self.params.iter() {
                if let Some(first) = values.first() {
                    dict.set_item(key, first)?;
                }
            }
            Ok(dict)
        }

        /// Equality ignores the order of keys (the order of values still matters).
        pub fn compare(&self, other: Self) -> bool {
            self.sorted() == other.sorted()
        }
    }

    impl Query {
        fn encode_with(&self, omit_empty_equal: bool) -> String {
            let mut parts = Vec::new();
            for (key, values) in self.params.iter() {
                let urlencoded_key: String = byte_serialize(key.as_bytes()).collect();
                for value in values.iter() {
                    if omit_empty_equal && value.is_empty() {
                        parts.push(urlencoded_key.clone());
                    } else {
                        let urlencoded_value: String = byte_serialize(value.as_bytes()).collect();
                        parts.push(format!("{urlencoded_key}={urlencoded_value}"));
                    }
                }
            }
            parts.join("&")
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
            self.segments.is_empty() || self.segments.last().is_none_or(|last| last.is_empty())
        }

        pub fn encode(&self) -> String {
            DUPLICATES_REGEX
                .replace_all(self.segments.join("/").as_str(), "/")
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

    /// Appends the segments of `extrapath` to `source` without any URL parsing:
    /// a segment is never cut at `?`/`#` and dot segments are kept literally
    /// (`normalize` resolves them). A fresh path remembers whether it is absolute
    /// (leading empty segment) and keeps interior empty segments as written.
    pub fn append_segments(source: &mut Vec<String>, extrapath: &str) {
        if extrapath.is_empty() {
            return;
        }
        let was_empty = source.is_empty();
        if source.last().is_some_and(|last| last.is_empty()) {
            source.pop();
        }
        if was_empty && extrapath.starts_with('/') {
            source.push(String::new());
        }
        let body = extrapath.trim_start_matches('/').trim_end_matches('/');
        if !body.is_empty() {
            for part in body.split('/') {
                if was_empty || !part.is_empty() {
                    source.push(encode_component(part, PATH_ALLOWED));
                }
            }
        }
        if extrapath.ends_with('/') {
            source.push(String::new());
        }
    }

    pub fn normalize(path: &str) -> String {
        let dedup = DUPLICATES_REGEX.replace_all(path, "/");
        let absolute = dedup.starts_with('/');
        let mut stack = Vec::<&str>::new();
        for segment in dedup.split('/') {
            match segment {
                ".." => match stack.last() {
                    Some(&last) if last != ".." => {
                        stack.pop();
                    }
                    _ if absolute => {}
                    _ => stack.push(".."),
                },
                "." | "" => continue,
                _ => stack.push(segment),
            }
        }
        let mut normalized = String::new();
        if absolute {
            normalized.push('/');
        }
        normalized.push_str(&stack.join("/"));
        if path.ends_with('/') && !stack.is_empty() {
            normalized.push('/');
        }
        normalized
    }

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
                fragment: encode_component(fragmentstr, FRAGMENT_ALLOWED),
            }
        }

        pub fn encode(&self) -> &str {
            self.fragment.as_str()
        }

        pub fn set(&mut self, fragmentstr: &str) {
            self.fragment = encode_component(fragmentstr, FRAGMENT_ALLOWED);
        }

        pub fn copy(&self) -> Self {
            self.clone()
        }

        pub fn compare(&self, other: Self) -> bool {
            self.fragment == other.fragment
        }
    }

    const INVALID_PORT: &str = "Invalid port received while parsing netloc.";

    /// Validates and normalizes a host (lowercase, punycode); empty is allowed.
    fn normalize_host(host: &str) -> PyResult<String> {
        if host.is_empty() {
            return Ok(String::new());
        }
        let invalid = || PyValueError::new_err(format!("Invalid host received: {host:?}."));
        let parsed = Url::parse(&format!("http://{host}")).map_err(|_| invalid())?;
        let clean = parsed.username().is_empty()
            && parsed.password().is_none()
            && parsed.port().is_none()
            && parsed.path() == "/"
            && parsed.query().is_none()
            && parsed.fragment().is_none();
        match parsed.host_str() {
            Some(normalized) if clean => Ok(normalized.to_string()),
            _ => Err(invalid()),
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
        fn empty() -> Self {
            Self {
                username: None,
                password: None,
                host: String::new(),
                port: None,
            }
        }

        fn is_empty(&self) -> bool {
            self.username.is_none()
                && self.password.is_none()
                && self.host.is_empty()
                && self.port.is_none()
        }

        /// Parses `user:pass@host:port` into a new value; nothing is mutated on error.
        fn parse_str(netloc: &str) -> PyResult<Self> {
            let (userinfo, hostport) = match netloc.rfind('@') {
                Some(at) => (Some(&netloc[..at]), &netloc[at + 1..]),
                None => (None, netloc),
            };
            let (host, port) = if hostport.starts_with('[') {
                let end = hostport.find(']').ok_or_else(|| {
                    PyValueError::new_err(format!("Invalid host received: {hostport:?}."))
                })?;
                let rest = &hostport[end + 1..];
                match rest.strip_prefix(':') {
                    Some(port) => (&hostport[..=end], port),
                    None if rest.is_empty() => (&hostport[..=end], ""),
                    None => return Err(PyValueError::new_err(INVALID_PORT)),
                }
            } else {
                match hostport.rfind(':') {
                    Some(colon) => (&hostport[..colon], &hostport[colon + 1..]),
                    None => (hostport, ""),
                }
            };
            let port = if port.is_empty() {
                None
            } else if port.bytes().all(|b| b.is_ascii_digit()) {
                Some(
                    port.parse::<u16>()
                        .map_err(|_| PyValueError::new_err(INVALID_PORT))?,
                )
            } else {
                return Err(PyValueError::new_err(INVALID_PORT));
            };
            let (username, password) = match userinfo {
                None => (None, None),
                Some(info) => match info.split_once(':') {
                    Some((user, pass)) => (
                        Some(encode_component(user, USERINFO_ALLOWED)),
                        Some(encode_component(pass, USERINFO_ALLOWED)),
                    ),
                    None if info.is_empty() => (None, None),
                    None => (Some(encode_component(info, USERINFO_ALLOWED)), None),
                },
            };
            Ok(Self {
                username,
                password,
                host: normalize_host(host)?,
                port,
            })
        }
    }

    #[pymethods]
    impl Netloc {
        #[new]
        pub fn new(netloc: &str) -> PyResult<Self> {
            Self::parse_str(netloc)
        }

        pub fn encode(&self) -> String {
            let mut netloc = String::new();
            if let Some(username) = &self.username {
                netloc.push_str(username);
                if let Some(password) = &self.password {
                    netloc.push(':');
                    netloc.push_str(password);
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
            *self = Self::parse_str(netloc)?;
            Ok(())
        }

        #[pyo3(signature = (host = None, port = None, username = None, password = None))]
        pub fn set(
            &mut self,
            host: Option<&str>,
            port: Option<u16>,
            username: Option<&str>,
            password: Option<&str>,
        ) -> PyResult<()> {
            let host = match host {
                Some(host) if !host.is_empty() => Some(normalize_host(host)?),
                _ => None,
            };
            if let Some(host) = host {
                self.host = host;
            }
            self.port = port.or(self.port);
            if let Some(username) = username {
                self.username = Some(encode_component(username, USERINFO_ALLOWED));
            }
            if let Some(password) = password {
                self.password = Some(encode_component(password, USERINFO_ALLOWED));
            }
            Ok(())
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
                port: self.port.or(other.port),
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
            self.port = other.port.or(self.port);
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
        ) -> PyResult<Self> {
            Ok(Self {
                host: normalize_host(host)?,
                port,
                username: username.map(|value| encode_component(value, USERINFO_ALLOWED)),
                password: password.map(|value| encode_component(value, USERINFO_ALLOWED)),
            })
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
            if number < 0 || number > u16::MAX as isize {
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

    /// The pieces of a URL reference (RFC 3986 appendix B), borrowed from the input.
    struct UrlParts<'a> {
        scheme: Option<&'a str>,
        authority: Option<&'a str>,
        path: &'a str,
        query: Option<&'a str>,
        fragment: Option<&'a str>,
    }

    fn is_scheme(candidate: &str) -> bool {
        let mut chars = candidate.chars();
        chars
            .next()
            .is_some_and(|first| first.is_ascii_alphabetic())
            && chars.all(|c| c.is_ascii_alphanumeric() || matches!(c, '+' | '-' | '.'))
    }

    fn split_url(val: &str) -> UrlParts<'_> {
        let (rest, fragment) = match val.split_once('#') {
            Some((rest, fragment)) => (rest, Some(fragment)),
            None => (val, None),
        };
        let (rest, query) = match rest.split_once('?') {
            Some((rest, query)) => (rest, Some(query)),
            None => (rest, None),
        };
        let (scheme, rest) = match rest.split_once(':') {
            Some((scheme, after)) if is_scheme(scheme) => (Some(scheme), after),
            _ => (None, rest),
        };
        let (authority, path) = match rest.strip_prefix("//") {
            Some(after) => match after.find('/') {
                Some(slash) => (Some(&after[..slash]), &after[slash..]),
                None => (Some(after), ""),
            },
            None => (None, rest),
        };
        UrlParts {
            scheme,
            authority,
            path,
            query,
            fragment,
        }
    }

    #[pyclass]
    #[allow(clippy::upper_case_acronyms)]
    pub struct URL {
        #[pyo3(get, set)]
        pub scheme: String,
        /// The reference had `//` (even with an empty host, as in `file:///x`).
        has_authority: bool,
        netloc: Py<Netloc>,
        path: Py<Path>,
        query: Py<Query>,
        fragment: Py<Fragment>,
    }

    impl URL {
        fn empty(py: Python<'_>) -> PyResult<Self> {
            Ok(Self {
                scheme: String::new(),
                has_authority: false,
                netloc: Py::new(py, Netloc::empty())?,
                path: Py::new(
                    py,
                    Path {
                        segments: Vec::new(),
                    },
                )?,
                query: Py::new(py, Query { params: Vec::new() })?,
                fragment: Py::new(
                    py,
                    Fragment {
                        fragment: String::new(),
                    },
                )?,
            })
        }

        fn replace_netloc(&mut self, py: Python<'_>, netloc: Netloc) {
            self.has_authority = !netloc.is_empty();
            *self.netloc.bind(py).borrow_mut() = netloc;
        }
    }

    #[pymethods]
    impl URL {
        #[new]
        pub fn new(py: Python<'_>, val: &str) -> PyResult<Self> {
            let val = val.trim_matches(|c: char| c <= ' ');
            let parts = split_url(val);
            let netloc = match parts.authority {
                Some(authority) => Netloc::parse_str(authority)
                    .map_err(|err| PyValueError::new_err(format!("Invalid URL {val:?}: {err}")))?,
                None => Netloc::empty(),
            };
            let mut instance = Self::empty(py)?;
            instance.scheme = parts.scheme.unwrap_or("").to_ascii_lowercase();
            instance.has_authority = parts.authority.is_some();
            *instance.netloc.bind(py).borrow_mut() = netloc;
            instance.path.bind(py).borrow_mut().add(parts.path);
            *instance.query.bind(py).borrow_mut() = Query::new(parts.query.unwrap_or(""));
            *instance.fragment.bind(py).borrow_mut() = Fragment::new(parts.fragment.unwrap_or(""));
            Ok(instance)
        }

        #[getter]
        pub fn get_netloc(&self, py: Python<'_>) -> Py<Netloc> {
            self.netloc.clone_ref(py)
        }

        #[setter]
        pub fn set_netloc(&mut self, py: Python<'_>, value: Netloc) {
            self.replace_netloc(py, value);
        }

        #[getter]
        pub fn get_path(&self, py: Python<'_>) -> Py<Path> {
            self.path.clone_ref(py)
        }

        #[setter]
        pub fn set_path(&mut self, py: Python<'_>, value: Path) {
            *self.path.bind(py).borrow_mut() = value;
        }

        #[getter]
        pub fn get_query(&self, py: Python<'_>) -> Py<Query> {
            self.query.clone_ref(py)
        }

        #[setter]
        pub fn set_query(&mut self, py: Python<'_>, value: Query) {
            *self.query.bind(py).borrow_mut() = value;
        }

        #[getter]
        pub fn get_fragment(&self, py: Python<'_>) -> Py<Fragment> {
            self.fragment.clone_ref(py)
        }

        #[setter]
        pub fn set_fragment(&mut self, py: Python<'_>, value: Fragment) {
            *self.fragment.bind(py).borrow_mut() = value;
        }

        #[pyo3(signature = (append_empty_equal = true))]
        pub fn encode(&self, py: Python<'_>, append_empty_equal: bool) -> String {
            let netloc = self.netloc.borrow(py).encode();
            let mut url = String::new();
            if !self.scheme.is_empty() {
                url.push_str(&self.scheme);
                url.push(':');
            }
            if self.has_authority || !netloc.is_empty() {
                url.push_str("//");
                url.push_str(&netloc);
            }

            let path = self.path.borrow(py).encode();
            let has_authority = self.has_authority || !netloc.is_empty();
            if has_authority && !path.is_empty() && !path.starts_with('/') {
                url.push('/');
            }
            url.push_str(&path);

            let query = self.query.borrow(py);
            let resolved_query = if append_empty_equal {
                query.encode()
            } else {
                query.omit_empty_equal()
            };
            if !resolved_query.is_empty() {
                url.push('?');
                url.push_str(&resolved_query);
            }

            let fragment = self.fragment.borrow(py);
            if !fragment.encode().is_empty() {
                url.push('#');
                url.push_str(fragment.encode());
            }
            url
        }

        #[pyo3(signature = (path = None, query = None, fragment = None, netloc = None, netloc_obj = None, scheme = None))]
        #[allow(clippy::too_many_arguments)]
        pub fn add(
            &mut self,
            py: Python<'_>,
            path: Option<&str>,
            query: Option<&Bound<'_, PyMapping>>,
            fragment: Option<&str>,
            netloc: Option<&str>,
            netloc_obj: Option<Netloc>,
            scheme: Option<&str>,
        ) -> PyResult<()> {
            // Fallible inputs first, so a failure leaves the URL untouched.
            let parsed_netloc = netloc.map(Netloc::parse_str).transpose()?;
            let pairs = query.map(mapping_pairs).transpose()?;

            if let Some(path) = path {
                self.path.bind(py).borrow_mut().add(path);
            }
            if let Some(pairs) = pairs {
                let mut query = self.query.bind(py).borrow_mut();
                for (key, value) in pairs {
                    query.add(key, value);
                }
            }
            if let Some(fragment) = fragment {
                self.fragment.bind(py).borrow_mut().set(fragment);
            }
            if let Some(parsed) = parsed_netloc {
                self.replace_netloc(py, parsed);
            }
            if let Some(netloc_obj) = netloc_obj {
                self.netloc.bind(py).borrow_mut().merge_inplace(netloc_obj);
                self.has_authority = self.has_authority || !self.netloc.borrow(py).is_empty();
            }
            if let Some(scheme) = scheme {
                self.scheme = scheme.to_string();
            }
            Ok(())
        }

        #[pyo3(signature = (path = None, query = None, fragment = None, netloc = None, netloc_obj = None, scheme = None))]
        #[allow(clippy::too_many_arguments)]
        pub fn set(
            &mut self,
            py: Python<'_>,
            path: Option<&str>,
            query: Option<&Bound<'_, PyMapping>>,
            fragment: Option<&str>,
            netloc: Option<&str>,
            netloc_obj: Option<Netloc>,
            scheme: Option<&str>,
        ) -> PyResult<()> {
            let parsed_netloc = netloc.map(Netloc::parse_str).transpose()?;
            let pairs = query.map(mapping_pairs).transpose()?;

            if let Some(path) = path {
                let mut current = self.path.bind(py).borrow_mut();
                current.clear();
                current.add(path);
            }
            if let Some(pairs) = pairs {
                let mut query = self.query.bind(py).borrow_mut();
                query.params.clear();
                for (key, value) in pairs {
                    query.set(key, value);
                }
            }
            if let Some(fragment) = fragment {
                self.fragment.bind(py).borrow_mut().set(fragment);
            }
            if let Some(parsed) = parsed_netloc {
                self.replace_netloc(py, parsed);
            }
            if let Some(netloc_obj) = netloc_obj {
                self.replace_netloc(py, netloc_obj);
            }
            if let Some(scheme) = scheme {
                self.scheme = scheme.to_string();
            }
            Ok(())
        }

        /// A deep copy: the parts are copied too, so the two URLs never share state.
        pub fn copy(&self, py: Python<'_>) -> PyResult<Self> {
            Ok(Self {
                scheme: self.scheme.clone(),
                has_authority: self.has_authority,
                netloc: Py::new(py, self.netloc.borrow(py).clone())?,
                path: Py::new(py, self.path.borrow(py).clone())?,
                query: Py::new(py, self.query.borrow(py).clone())?,
                fragment: Py::new(py, self.fragment.borrow(py).clone())?,
            })
        }

        #[staticmethod]
        #[pyo3(signature = (netloc = None, username = None, password  = None, host = None, port = None))]
        pub fn from_netloc(
            py: Python<'_>,
            netloc: Option<Netloc>,
            username: Option<&str>,
            password: Option<&str>,
            host: Option<&str>,
            port: Option<u16>,
        ) -> PyResult<Self> {
            let mut netloc_instance =
                Netloc::from_args(host.unwrap_or(""), port, username, password)?;
            if let Some(netloc) = netloc {
                netloc_instance = netloc_instance.merge_left(netloc);
            }
            let mut url = Self::empty(py)?;
            url.replace_netloc(py, netloc_instance);
            Ok(url)
        }

        #[staticmethod]
        #[pyo3(signature = (path = None, query = None, fragment = None, netloc = None, netloc_obj = None, scheme = None))]
        pub fn from_args(
            py: Python<'_>,
            path: Option<&str>,
            query: Option<&Bound<'_, PyMapping>>,
            fragment: Option<&str>,
            netloc: Option<&str>,
            netloc_obj: Option<Netloc>,
            scheme: Option<&str>,
        ) -> PyResult<Self> {
            let mut url = Self::empty(py)?;
            url.set(py, path, query, fragment, netloc, netloc_obj, scheme)?;
            Ok(url)
        }

        pub fn compare(&self, py: Python<'_>, other: PyRef<'_, URL>) -> bool {
            self.scheme == other.scheme
                && self
                    .query
                    .borrow(py)
                    .compare(other.query.borrow(py).clone())
                && self.path.borrow(py).compare(other.path.borrow(py).clone())
                && self
                    .netloc
                    .borrow(py)
                    .compare(other.netloc.borrow(py).clone())
                && self
                    .fragment
                    .borrow(py)
                    .compare(other.fragment.borrow(py).clone())
        }
    }
}
