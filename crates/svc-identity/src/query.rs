//! A minimal query-string reader (`a=b&c=d`, percent-decoded), so no extra HTTP dependency is
//! needed for the few list filters.

use std::collections::HashMap;

/// The decoded parameters; a repeated name keeps its last value, bad escapes are kept as typed.
pub(crate) fn parse(raw: Option<&str>) -> HashMap<String, String> {
    raw.unwrap_or_default()
        .split('&')
        .filter(|pair| !pair.is_empty())
        .map(|pair| pair.split_once('=').unwrap_or((pair, "")))
        .map(|(name, value)| (decode(name), decode(value)))
        .collect()
}

fn decode(text: &str) -> String {
    let bytes = text.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut index = 0;
    while let Some(&byte) = bytes.get(index) {
        let (value, used) = unescape(bytes, index, byte);
        out.push(value);
        index += used;
    }
    String::from_utf8_lossy(&out).into_owned()
}

/// The byte a position stands for and how many input bytes it used.
fn unescape(bytes: &[u8], index: usize, byte: u8) -> (u8, usize) {
    let escaped = bytes.get(index + 1..index + 3).and_then(hex_pair);
    match (byte, escaped) {
        (b'%', Some(value)) => (value, 3),
        (b'+', _) => (b' ', 1),
        (other, _) => (other, 1),
    }
}

fn hex_pair(pair: &[u8]) -> Option<u8> {
    let text = std::str::from_utf8(pair).ok()?;
    u8::from_str_radix(text, 16).ok()
}

#[cfg(test)]
mod tests {
    use super::parse;

    #[test]
    fn decodes_names_values_plus_and_percent() {
        let found = parse(Some("q=a%40b+c&status=active&flag&bad=%zz"));
        assert_eq!(found.get("q").map(String::as_str), Some("a@b c"));
        assert_eq!(found.get("status").map(String::as_str), Some("active"));
        assert_eq!(found.get("flag").map(String::as_str), Some(""));
        assert_eq!(found.get("bad").map(String::as_str), Some("%zz"));
    }

    #[test]
    fn no_query_is_empty() {
        assert!(parse(None).is_empty());
    }
}
