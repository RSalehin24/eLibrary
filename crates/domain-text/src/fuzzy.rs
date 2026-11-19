use crate::keys::ExactKey;

const NUKTA: char = '\u{09BC}';
const BENGALI_YA: char = 'য';

/// Key for tolerant matching: an exact key plus Bengali spelling-variant folding.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct FuzzyKey(String);

impl FuzzyKey {
    #[must_use]
    pub fn new(raw: &str) -> Self {
        Self(fold_spelling(&ExactKey::new(raw).into_string()))
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

// Every mapping is one char to one char (or drops a nukta), so a key never grows.
fn fold_spelling(exact: &str) -> String {
    let mut previous = None;
    exact
        .chars()
        .filter(|c| {
            let is_ya_nukta = *c == NUKTA && previous == Some(BENGALI_YA);
            previous = Some(*c);
            !is_ya_nukta
        })
        .map(fold_char)
        .collect()
}

fn fold_char(c: char) -> char {
    match c {
        'ঈ' => 'ই',
        'ঊ' => 'উ',
        '\u{09C0}' => '\u{09BF}',
        '\u{09C2}' => '\u{09C1}',
        'শ' | 'ষ' => 'স',
        'ণ' => 'ন',
        other => other,
    }
}
