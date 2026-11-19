use unicode_normalization::{UnicodeNormalization, char::canonical_combining_class};

const ZERO_WIDTH_NON_JOINER: char = '\u{200C}';
const ZERO_WIDTH_JOINER: char = '\u{200D}';
const BENGALI_BLOCK: std::ops::RangeInclusive<char> = '\u{0980}'..='\u{09FF}';
const BENGALI_DIGIT_ZERO: u32 = 0x09E6;
const BENGALI_DIGIT_NINE: u32 = 0x09EF;

/// Key for exact matching. Never applies spelling-variant folding.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ExactKey(String);

impl ExactKey {
    #[must_use]
    pub fn new(raw: &str) -> Self {
        // why: filtering can make marks adjacent out of canonical order, so normalize once more.
        let folded: String = raw
            .nfkc()
            .flat_map(char::to_lowercase)
            .nfkc()
            .filter(|c| *c != ZERO_WIDTH_JOINER && *c != ZERO_WIDTH_NON_JOINER)
            .map(fold_digit)
            .filter(|c| c.is_whitespace() || is_letter_mark_or_digit(*c))
            .collect::<String>()
            .nfkc()
            .collect();
        Self(collapse_whitespace(&folded))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

fn fold_digit(c: char) -> char {
    let code = u32::from(c);
    if (BENGALI_DIGIT_ZERO..=BENGALI_DIGIT_NINE).contains(&code) {
        let ascii = u32::from('0') + (code - BENGALI_DIGIT_ZERO);
        return char::from_u32(ascii).unwrap_or(c);
    }
    c
}

// why: std has no "is a mark" test; Bengali signs are not alphanumeric, so the whole block counts.
fn is_letter_mark_or_digit(c: char) -> bool {
    c.is_alphanumeric()
        || BENGALI_BLOCK.contains(&c) && !is_bengali_punctuation(c)
        || canonical_combining_class(c) != 0
}

fn is_bengali_punctuation(c: char) -> bool {
    matches!(c, '\u{09F2}'..='\u{09FE}')
}

fn collapse_whitespace(text: &str) -> String {
    text.split_whitespace().collect::<Vec<_>>().join(" ")
}

impl ExactKey {
    pub(crate) fn into_string(self) -> String {
        self.0
    }
}
