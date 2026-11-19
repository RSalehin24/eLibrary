const DIGITS: &[u8; 16] = b"0123456789abcdef";
const HIGH_NIBBLE_SHIFT: u32 = 4;
const LOW_NIBBLE_MASK: u8 = 0x0f;

pub(crate) fn encode(bytes: &[u8]) -> String {
    bytes
        .iter()
        .flat_map(|byte| [byte >> HIGH_NIBBLE_SHIFT, byte & LOW_NIBBLE_MASK])
        .filter_map(|nibble| DIGITS.get(usize::from(nibble)).copied())
        .map(char::from)
        .collect()
}

/// `None` unless the text is an even number of lowercase hex digits.
pub(crate) fn decode(text: &str) -> Option<Vec<u8>> {
    if !text.len().is_multiple_of(2) {
        return None;
    }
    text.as_bytes().chunks(2).map(decode_pair).collect()
}

fn decode_pair(pair: &[u8]) -> Option<u8> {
    let digits = std::str::from_utf8(pair).ok()?;
    if !digits
        .bytes()
        .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    {
        return None;
    }
    u8::from_str_radix(digits, 16).ok()
}
