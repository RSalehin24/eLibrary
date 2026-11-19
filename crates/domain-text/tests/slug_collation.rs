use std::cmp::Ordering;

use domain_text::{BengaliCollator, CollationUnavailable, Slug};

#[test]
fn slug_keeps_bengali_letters_and_joins_words_with_hyphens() {
    let slug = Slug::from_title("বাংলা ভাষা, ২য় খণ্ড!").map(|s| s.as_str().to_owned());
    assert_eq!(slug.as_deref(), Some("বাংলা-ভাষা-2য়-খণ্ড"));
}

#[test]
fn slug_of_text_without_letters_is_none() {
    assert_eq!(Slug::from_title(" !?। "), None);
}

#[test]
fn collator_orders_bengali_alphabetically() -> Result<(), CollationUnavailable> {
    let collator = BengaliCollator::new()?;
    assert_eq!(collator.compare("অ", "আ"), Ordering::Less);
    assert_eq!(collator.compare("কলম", "খাতা"), Ordering::Less);
    assert_eq!(collator.compare("খাতা", "কলম"), Ordering::Greater);
    Ok(())
}

#[test]
fn sort_key_order_matches_comparator() -> Result<(), CollationUnavailable> {
    let collator = BengaliCollator::new()?;
    let words = ["খাতা", "অ", "কলম", "আম", "apple"];
    let pairs = words
        .iter()
        .flat_map(|left| words.iter().map(move |right| (*left, *right)));
    for (left, right) in pairs {
        let by_key = collator.sort_key(left).cmp(&collator.sort_key(right));
        assert_eq!(by_key, collator.compare(left, right), "{left} vs {right}");
    }
    Ok(())
}
