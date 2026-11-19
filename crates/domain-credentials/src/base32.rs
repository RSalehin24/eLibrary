//! RFC 4648 base32 (the alphabet authenticator apps use), without padding on output.

const ALPHABET: &[u8; 32] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ234567";
const BITS_PER_CHAR: usize = 5;
const BITS_PER_BYTE: usize = 8;

pub(crate) fn encode(bytes: &[u8]) -> String {
    let bits: Vec<u8> = bytes
        .iter()
        .flat_map(|byte| bits_of(u32::from(*byte), BITS_PER_BYTE))
        .collect();
    bits.chunks(BITS_PER_CHAR)
        .filter_map(char_for_chunk)
        .collect()
}

fn bits_of(value: u32, width: usize) -> impl Iterator<Item = u8> {
    (0..width)
        .rev()
        .map(move |shift| u8::from((value >> shift) & 1 == 1))
}

/// A final short chunk is padded with zero bits on the right.
fn char_for_chunk(chunk: &[u8]) -> Option<char> {
    let value = chunk
        .iter()
        .fold(0usize, |acc, bit| (acc << 1) | usize::from(*bit));
    let padded = value << (BITS_PER_CHAR - chunk.len());
    ALPHABET.get(padded).copied().map(char::from)
}

/// Accepts upper or lower case, ignores spaces and `=` padding; `None` for anything else.
pub(crate) fn decode(text: &str) -> Option<Vec<u8>> {
    let values: Option<Vec<u32>> = text
        .chars()
        .filter(|c| *c != '=' && !c.is_whitespace())
        .map(value_of)
        .collect();
    let bits: Vec<u8> = values?
        .into_iter()
        .flat_map(|value| bits_of(value, BITS_PER_CHAR))
        .collect();
    Some(
        bits.as_chunks::<BITS_PER_BYTE>()
            .0
            .iter()
            .map(|byte| byte.iter().fold(0u8, |acc, bit| (acc << 1) | *bit))
            .collect(),
    )
}

fn value_of(c: char) -> Option<u32> {
    let upper = c.to_ascii_uppercase();
    let index = ALPHABET
        .iter()
        .position(|letter| char::from(*letter) == upper)?;
    u32::try_from(index).ok()
}
