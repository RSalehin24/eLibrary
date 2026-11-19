use domain_text::{DisplayText, ExactKey, FuzzyKey};
use proptest::prelude::*;

#[test]
fn display_text_is_nfc_and_keeps_joiners() {
    let decomposed = "e\u{0301}\u{200D}";
    assert_eq!(DisplayText::new(decomposed).as_str(), "\u{e9}\u{200D}");
}

#[test]
fn exact_key_folds_case_digits_punctuation_whitespace_and_joiners() {
    let key = ExactKey::new("  Hello,\u{200C}  WORLD! ১২৩ ");
    assert_eq!(key.as_str(), "hello world 123");
}

#[test]
fn exact_key_keeps_bengali_letters_and_signs() {
    assert_eq!(ExactKey::new("বাংলা।").as_str(), "বাংলা");
}

#[test]
fn exact_key_does_not_fold_spelling_but_fuzzy_key_does() {
    assert_ne!(ExactKey::new("শহর").as_str(), ExactKey::new("সহর").as_str());
    assert_eq!(FuzzyKey::new("শহর"), FuzzyKey::new("সহর"));
    assert_eq!(FuzzyKey::new("বাড়ী"), FuzzyKey::new("বাড়ি"));
    assert_eq!(FuzzyKey::new("য়"), FuzzyKey::new("য"));
}

proptest! {
    #[test]
    fn exact_key_is_idempotent(raw in "\\PC*") {
        let once = ExactKey::new(&raw);
        prop_assert_eq!(ExactKey::new(once.as_str()), once);
    }

    #[test]
    fn display_text_is_idempotent(raw in "\\PC*") {
        let once = DisplayText::new(&raw);
        prop_assert_eq!(DisplayText::new(once.as_str()), once);
    }

    #[test]
    fn fuzzy_key_never_longer_than_exact_key(raw in "\\PC*") {
        prop_assert!(FuzzyKey::new(&raw).as_str().chars().count() <= ExactKey::new(&raw).as_str().chars().count());
    }

    #[test]
    fn fuzzy_key_is_idempotent(raw in "\\PC*") {
        let once = FuzzyKey::new(&raw);
        prop_assert_eq!(FuzzyKey::new(once.as_str()), once);
    }
}
