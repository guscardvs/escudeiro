use pyo3::pymodule;

/// Pure string logic, kept outside the `#[pymodule]` so it can be unit tested
/// without a Python interpreter.
mod text {
    use regex::Regex;
    use std::collections::HashMap;

    /// Replace every occurrence of every key in a single left-to-right pass.
    /// At each position the longest matching key wins; replaced text is never
    /// rescanned, so the result does not depend on map iteration order.
    pub fn replace_many<'a, I>(value: &str, pairs: I) -> Result<String, regex::Error>
    where
        I: IntoIterator<Item = (&'a str, &'a str)>,
    {
        let lookup: HashMap<&str, &str> =
            pairs.into_iter().filter(|(k, _)| !k.is_empty()).collect();
        if lookup.is_empty() {
            return Ok(value.to_string());
        }
        let mut keys: Vec<&str> = lookup.keys().copied().collect();
        // Regex alternation is leftmost-first, so longest-first ordering yields leftmost-longest.
        keys.sort_by(|a, b| b.len().cmp(&a.len()).then_with(|| a.cmp(b)));
        let pattern = keys
            .iter()
            .map(|k| regex::escape(k))
            .collect::<Vec<_>>()
            .join("|");
        let re = Regex::new(&pattern)?;
        Ok(re
            .replace_all(value, |caps: &regex::Captures| lookup[&caps[0]].to_string())
            .into_owned())
    }

    /// `(leading underscores, words, trailing underscores)`.
    ///
    /// Words are separated by `_`, `-` and whitespace. Inside a separator-free
    /// segment a new word starts at an uppercase letter that follows a
    /// lowercase letter or a digit (`getHTTP` -> `get|HTTP`, `var1Name` ->
    /// `var1|Name`), and at the last capital of an uppercase run that is
    /// followed by a lowercase letter (`HTTPServer` -> `HTTP|Server`,
    /// `OAuth2Client` -> `O|Auth2|Client`). Digits stay attached to the word
    /// before them.
    pub fn split_words(value: &str) -> (String, Vec<String>, String) {
        let lead: String = value.chars().take_while(|c| *c == '_').collect();
        let rest = &value[lead.len()..];
        let trimmed = rest.trim_end_matches('_');
        let trail = rest[trimmed.len()..].to_string();

        let mut words = Vec::new();
        for segment in trimmed.split(|c: char| c == '_' || c == '-' || c.is_whitespace()) {
            let chars: Vec<char> = segment.chars().collect();
            let mut start = 0;
            for i in 1..chars.len() {
                let (prev, cur) = (chars[i - 1], chars[i]);
                let next_is_lower = chars.get(i + 1).is_some_and(|n| n.is_lowercase());
                let boundary = cur.is_uppercase()
                    && (prev.is_lowercase()
                        || prev.is_ascii_digit()
                        || (prev.is_uppercase() && next_is_lower));
                if boundary {
                    words.push(chars[start..i].iter().collect::<String>());
                    start = i;
                }
            }
            if start < chars.len() {
                words.push(chars[start..].iter().collect::<String>());
            }
        }
        (lead, words, trail)
    }

    fn capitalize(word: &str) -> String {
        let mut chars = word.chars();
        match chars.next() {
            None => String::new(),
            Some(first) => first
                .to_uppercase()
                .chain(chars.flat_map(char::to_lowercase))
                .collect(),
        }
    }

    pub fn snake(value: &str) -> String {
        let (lead, words, trail) = split_words(value);
        let body = words
            .iter()
            .map(|w| w.to_lowercase())
            .collect::<Vec<_>>()
            .join("_");
        format!("{lead}{body}{trail}")
    }

    /// camelCase/PascalCase drop trailing underscores of a plain name, where they only
    /// escape a keyword (`type_` -> `type`); private and dunder names (`_x`, `__init__`)
    /// keep both ends.
    fn keep_trail<'a>(lead: &str, trail: &'a str) -> &'a str {
        if lead.is_empty() { "" } else { trail }
    }

    pub fn camel(value: &str) -> String {
        let (lead, words, trail) = split_words(value);
        let body: String = words
            .iter()
            .enumerate()
            .map(|(i, w)| {
                if i == 0 {
                    w.to_lowercase()
                } else {
                    capitalize(w)
                }
            })
            .collect();
        format!("{lead}{body}{}", keep_trail(&lead, &trail))
    }

    pub fn pascal(value: &str) -> String {
        let (lead, words, trail) = split_words(value);
        let body: String = words.iter().map(|w| capitalize(w)).collect();
        format!("{lead}{body}{}", keep_trail(&lead, &trail))
    }

    pub fn kebab(value: &str, remove_trailing_underscores: bool) -> String {
        let (lead, words, trail) = split_words(value);
        let body = words
            .iter()
            .map(|w| w.to_lowercase())
            .collect::<Vec<_>>()
            .join("-");
        let trail = if remove_trailing_underscores {
            ""
        } else {
            trail.as_str()
        };
        format!("{lead}{body}{trail}")
    }

    pub fn terminate(value: &str, mark: char) -> String {
        if value.is_empty() || value.ends_with(['.', '?', '!']) {
            value.to_string()
        } else {
            format!("{value}{mark}")
        }
    }

    #[cfg(test)]
    mod tests {
        use super::*;

        #[test]
        fn replace_many_is_single_pass_and_longest_first() {
            for _ in 0..50 {
                let pairs = [("a", "b"), ("b", "c")];
                assert_eq!(replace_many("ab", pairs).unwrap(), "bc");
            }
            assert_eq!(
                replace_many("abc", [("a", "x"), ("ab", "y")]).unwrap(),
                "yc"
            );
            assert_eq!(replace_many("a.b", [(".", "!")]).unwrap(), "a!b");
            assert_eq!(replace_many("abc", [("", "x")]).unwrap(), "abc");
            assert_eq!(replace_many("abc", []).unwrap(), "abc");
        }

        #[test]
        fn case_table() {
            // (input, snake, camel, pascal, kebab)
            let table = [
                (
                    "CamelCase",
                    "camel_case",
                    "camelCase",
                    "CamelCase",
                    "camel-case",
                ),
                (
                    "camel case",
                    "camel_case",
                    "camelCase",
                    "CamelCase",
                    "camel-case",
                ),
                (
                    "HTTPServer",
                    "http_server",
                    "httpServer",
                    "HttpServer",
                    "http-server",
                ),
                (
                    "getHTTPResponse",
                    "get_http_response",
                    "getHttpResponse",
                    "GetHttpResponse",
                    "get-http-response",
                ),
                (
                    "XMLHttpRequest",
                    "xml_http_request",
                    "xmlHttpRequest",
                    "XmlHttpRequest",
                    "xml-http-request",
                ),
                (
                    "OAuth2Client",
                    "o_auth2_client",
                    "oAuth2Client",
                    "OAuth2Client",
                    "o-auth2-client",
                ),
                ("var1Name", "var1_name", "var1Name", "Var1Name", "var1-name"),
                (
                    "item_2_name",
                    "item_2_name",
                    "item2Name",
                    "Item2Name",
                    "item-2-name",
                ),
                ("_private", "_private", "_private", "_Private", "_private"),
                ("__init__", "__init__", "__init__", "__Init__", "__init__"),
                ("ABC", "abc", "abc", "Abc", "abc"),
                // trailing underscore of a plain name only escapes a keyword
                ("type_", "type_", "type", "Type", "type_"),
                (
                    "camel_case_",
                    "camel_case_",
                    "camelCase",
                    "CamelCase",
                    "camel-case_",
                ),
                ("_x_", "_x_", "_x_", "_X_", "_x_"),
                ("", "", "", "", ""),
                ("___", "___", "___", "___", "___"),
            ];
            for (input, snake_, camel_, pascal_, kebab_) in table {
                assert_eq!(snake(input), snake_, "snake({input})");
                assert_eq!(camel(input), camel_, "camel({input})");
                assert_eq!(pascal(input), pascal_, "pascal({input})");
                assert_eq!(kebab(input, false), kebab_, "kebab({input})");
            }
        }

        #[test]
        fn kebab_trailing_underscores() {
            assert_eq!(kebab("camel_case_", true), "camel-case");
            assert_eq!(kebab("camel_case_", false), "camel-case_");
        }

        #[test]
        fn terminate_keeps_existing_mark() {
            assert_eq!(terminate("Hi", '.'), "Hi.");
            assert_eq!(terminate("Really?!", '.'), "Really?!");
            assert_eq!(terminate("Done.", '.'), "Done.");
            assert_eq!(terminate("", '.'), "");
        }
    }
}

#[pymodule]
pub mod strings {
    use super::text;
    use pyo3::{PyResult, exceptions::PyValueError, pyfunction};
    use std::collections::HashMap;

    /// Replace every key of `replacements` in a single pass (leftmost-longest).
    #[pyfunction]
    fn replace_all(value: String, replacements: HashMap<String, String>) -> PyResult<String> {
        text::replace_many(
            &value,
            replacements.iter().map(|(k, v)| (k.as_str(), v.as_str())),
        )
        .map_err(|e| PyValueError::new_err(format!("invalid replacements: {e}")))
    }

    /// Replace every needle with `replacement` in a single pass.
    #[pyfunction]
    fn replace_by(value: &str, replacement: &str, to_replace: Vec<String>) -> PyResult<String> {
        text::replace_many(value, to_replace.iter().map(|k| (k.as_str(), replacement)))
            .map_err(|e| PyValueError::new_err(format!("invalid replacements: {e}")))
    }

    #[pyfunction]
    fn to_snake(value: &str) -> String {
        text::snake(value)
    }

    #[pyfunction]
    fn to_camel(value: &str) -> String {
        text::camel(value)
    }

    #[pyfunction]
    fn to_pascal(value: &str) -> String {
        text::pascal(value)
    }

    #[pyfunction]
    #[pyo3(signature = (value, remove_trailing_underscores = true))]
    fn to_kebab(value: &str, remove_trailing_underscores: bool) -> String {
        text::kebab(value, remove_trailing_underscores)
    }

    #[pyfunction]
    fn squote(value: String) -> String {
        format!("'{value}'")
    }

    #[pyfunction]
    fn dquote(value: String) -> String {
        format!("\"{value}\"")
    }

    fn trim_punctiation(value: char) -> bool {
        ['.', '!', '?'].contains(&value)
    }

    /// Append `.` unless the value already ends with `.`, `?` or `!`; empty stays empty.
    #[pyfunction]
    fn sentence(value: String) -> String {
        text::terminate(&value, '.')
    }

    #[pyfunction]
    fn exclamation(value: String) -> String {
        format!(
            "{formatted}!",
            formatted = value.trim_end_matches(trim_punctiation)
        )
    }

    #[pyfunction]
    fn question(value: String) -> String {
        format!(
            "{formatted}?",
            formatted = value.trim_end_matches(trim_punctiation)
        )
    }
}
