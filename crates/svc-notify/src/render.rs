//! Renders the plain-text mail for a request fetched from identity (REQ-NTF-003). The address
//! and the link never appear in the subject; the link appears once in the body.

use serde::Deserialize;

use crate::transport::OutgoingMail;

/// What identity returns for `GET /internal/email-requests/{request_id}`.
#[derive(Clone, Deserialize)]
pub struct MailRequest {
    pub kind: String,
    pub to: String,
    pub language: String,
    pub link: String,
}

impl std::fmt::Debug for MailRequest {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MailRequest")
            .field("kind", &self.kind)
            .field("language", &self.language)
            .finish_non_exhaustive()
    }
}

/// The fixed words of one mail: subject, text before the link, text after it.
struct Words {
    subject: &'static str,
    before: &'static str,
    after: &'static str,
}

const INVITE_EN: Words = Words {
    subject: "You are invited to the library",
    before: "An account has been created for you in the library. Open this link to choose your password:",
    after: "If you were not expecting this invitation, you can ignore this message.",
};
const INVITE_BN: Words = Words {
    subject: "লাইব্রেরিতে আপনাকে আমন্ত্রণ জানানো হয়েছে",
    before: "লাইব্রেরিতে আপনার জন্য একটি অ্যাকাউন্ট তৈরি করা হয়েছে। পাসওয়ার্ড ঠিক করতে নিচের লিংকটি খুলুন:",
    after: "আপনি এই আমন্ত্রণের অপেক্ষায় না থাকলে এই বার্তাটি উপেক্ষা করতে পারেন।",
};
const RESET_EN: Words = Words {
    subject: "Reset your library password",
    before: "We received a request to reset your password. Open this link to choose a new one:",
    after: "If you did not ask for this, you can ignore this message; your password stays the same.",
};
const RESET_BN: Words = Words {
    subject: "আপনার লাইব্রেরির পাসওয়ার্ড রিসেট করুন",
    before: "আপনার পাসওয়ার্ড রিসেট করার একটি অনুরোধ পেয়েছি। নতুন পাসওয়ার্ড ঠিক করতে নিচের লিংকটি খুলুন:",
    after: "আপনি এটি না চাইলে এই বার্তাটি উপেক্ষা করুন; আপনার পাসওয়ার্ড অপরিবর্তিত থাকবে।",
};
const CHANGED_EN: Words = Words {
    subject: "Your library password was changed",
    before: "The password of your library account was just changed.",
    after: "If this was not you, contact the library administrator at once.",
};
const CHANGED_BN: Words = Words {
    subject: "আপনার লাইব্রেরির পাসওয়ার্ড পরিবর্তন করা হয়েছে",
    before: "আপনার লাইব্রেরি অ্যাকাউন্টের পাসওয়ার্ড এইমাত্র পরিবর্তন করা হয়েছে।",
    after: "এটি আপনি না করে থাকলে এখনই লাইব্রেরির প্রশাসকের সঙ্গে যোগাযোগ করুন।",
};

fn words(kind: &str, language: &str) -> Option<(&'static Words, bool)> {
    match (kind, language) {
        ("invite", "en") => Some((&INVITE_EN, true)),
        ("invite", "bn") => Some((&INVITE_BN, true)),
        ("password_reset", "en") => Some((&RESET_EN, true)),
        ("password_reset", "bn") => Some((&RESET_BN, true)),
        ("password_changed", "en") => Some((&CHANGED_EN, false)),
        ("password_changed", "bn") => Some((&CHANGED_BN, false)),
        _ => None,
    }
}

/// The mail for `request`, or `None` for an unknown kind or language.
#[must_use]
pub fn render(request: &MailRequest) -> Option<OutgoingMail> {
    let (words, has_link) = words(&request.kind, &request.language)?;
    let text = if has_link {
        format!("{}\n\n{}\n\n{}\n", words.before, request.link, words.after)
    } else {
        format!("{}\n\n{}\n", words.before, words.after)
    };
    Some(OutgoingMail {
        to: request.to.clone(),
        subject: words.subject.to_owned(),
        text,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    const LINK: &str = "https://library.test/reset/SECRET-TOKEN";

    fn request(kind: &str, language: &str) -> MailRequest {
        MailRequest {
            kind: kind.to_owned(),
            to: "reader@example.org".to_owned(),
            language: language.to_owned(),
            link: LINK.to_owned(),
        }
    }

    const PAIRS: [(&str, &str); 6] = [
        ("invite", "bn"),
        ("invite", "en"),
        ("password_reset", "bn"),
        ("password_reset", "en"),
        ("password_changed", "bn"),
        ("password_changed", "en"),
    ];

    fn sound(mail: &OutgoingMail) -> bool {
        mail.to == "reader@example.org"
            && !mail.subject.is_empty()
            && !mail.text.is_empty()
            && !mail.subject.contains(LINK)
            && !mail.subject.contains("reader@example.org")
            && !mail.text.contains("reader@example.org")
    }

    fn link_count((kind, language): (&str, &str)) -> usize {
        render(&request(kind, language)).map_or(usize::MAX, |mail| mail.text.matches(LINK).count())
    }

    fn expected((kind, _): (&str, &str)) -> usize {
        usize::from(kind != "password_changed")
    }

    fn renders_soundly((kind, language): (&str, &str)) -> bool {
        render(&request(kind, language)).is_some_and(|mail| sound(&mail))
    }

    fn is_bengali(c: char) -> bool {
        ('\u{0980}'..='\u{09FF}').contains(&c)
    }

    #[test]
    fn every_kind_and_language_renders() {
        assert!(PAIRS.into_iter().all(renders_soundly));
    }

    #[test]
    fn link_appears_exactly_once_where_there_is_one() {
        assert_eq!(PAIRS.map(link_count), PAIRS.map(expected));
    }

    #[test]
    fn bengali_is_bengali_and_english_is_ascii() {
        let bn = render(&request("invite", "bn"));
        assert!(bn.is_some_and(|m| m.subject.chars().any(is_bengali)));
        let en = render(&request("invite", "en"));
        assert!(en.is_some_and(|m| m.subject.is_ascii()));
    }

    #[test]
    fn unknown_kind_or_language_is_none() {
        assert!(render(&request("welcome", "en")).is_none());
        assert!(render(&request("invite", "fr")).is_none());
    }

    #[test]
    fn debug_hides_address_and_link() {
        let shown = format!("{:?}", request("invite", "en"));
        assert!(!shown.contains("example.org") && !shown.contains("SECRET"));
    }
}
