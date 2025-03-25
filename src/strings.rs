use pyo3::pymodule;

#[pymodule]
pub mod strings {
    use once_cell::sync::Lazy;
    use pyo3::pyfunction;
    use regex::{Captures, Regex};
    use std::collections::HashMap;

    #[pyfunction]
    fn replace_all(value: String, replacements: HashMap<String, String>) -> String {
        replacements
            .iter()
            .fold(value.clone(), |acc, (to_replace, replacement)| {
                acc.replace(to_replace, replacement)
            })
    }

    #[pyfunction]
    fn replace_by(value: &str, replacement: &str, to_replace: Vec<String>) -> String {
        to_replace.iter().fold(value.to_string(), |acc, needle| {
            acc.replace(needle, replacement)
        })
    }

    static CAMEL_CASE_REGEX: Lazy<Regex> = Lazy::new(|| Regex::new("([a-z])([A-Z])").unwrap());
    static SNAKE_KEBAB_CASE_REGEX: Lazy<Regex> =
        Lazy::new(|| Regex::new("(_|-)([a-zA-Z])").unwrap());

    #[pyfunction]
    fn to_snake(value: String) -> String {
        replace_by(
            &CAMEL_CASE_REGEX.replace_all(value.as_str(), "${1}_${2}"),
            "_",
            Vec::from(vec![String::from("-"), String::from(" ")]),
        )
        .to_lowercase()
    }

    #[pyfunction]
    fn to_camel(value: String) -> String {
        SNAKE_KEBAB_CASE_REGEX
            .replace_all(to_snake(value).as_str(), |val: &Captures| {
                val[2].to_uppercase()
            })
            .trim_end_matches("_")
            .to_string()
    }

    #[pyfunction]
    fn to_pascal(value: String) -> String {
        if value.is_empty() {
            return value;
        }
        let camelized = to_camel(value);
        [
            camelized.get(..1).unwrap().to_uppercase(),
            camelized.get(1..).unwrap().to_string(),
        ]
        .join("")
    }

    #[pyfunction]
    #[pyo3(signature = (value, remove_trailing_underscores = true))]
    fn to_kebab(value: String, remove_trailing_underscores: bool) -> String {
        let result = to_snake(value).replace("_", "-");
        if remove_trailing_underscores {
            result.trim_end_matches("-").to_string()
        } else {
            result
        }
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

    #[pyfunction]
    fn sentence(value: String) -> String {
        format!(
            "{formatted}.",
            formatted = value.trim_end_matches(trim_punctiation)
        )
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
