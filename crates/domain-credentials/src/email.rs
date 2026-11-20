//! Validated email addresses: the account address and the Kindle delivery address
//! (REQ-IDN-028, INV-IDN-028).

use thiserror::Error;

const ADDRESS_MAX_CHARS: usize = 254;
const LOCAL_MAX_CHARS: usize = 64;
const LABEL_MAX_CHARS: usize = 63;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Error)]
#[error("not a valid email address")]
pub struct EmailError;

/// The old name of [`EmailError`], kept for the Kindle address type.
pub type KindleEmailError = EmailError;

/// A plain ASCII `local@domain.tld` address, lower-cased. Quoted or comment forms are refused.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Email(String);

impl Email {
    /// # Errors
    /// [`EmailError`] when the text is not a plain address.
    pub fn parse(text: &str) -> Result<Self, EmailError> {
        let text = text.trim().to_ascii_lowercase();
        let valid = text.len() <= ADDRESS_MAX_CHARS
            && text
                .split_once('@')
                .is_some_and(|(local, domain)| valid_local(local) && valid_domain(domain));
        valid.then_some(Self(text)).ok_or(EmailError)
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

/// A Kindle delivery address: an [`Email`] used as the target of a send-to-Kindle mail.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct KindleEmail(Email);

impl KindleEmail {
    /// # Errors
    /// [`EmailError`] when the text is not a plain address.
    pub fn parse(text: &str) -> Result<Self, EmailError> {
        Email::parse(text).map(Self)
    }

    #[must_use]
    pub fn as_str(&self) -> &str {
        self.0.as_str()
    }
}

fn valid_local(local: &str) -> bool {
    let atom = |byte: u8| byte.is_ascii_alphanumeric() || b"!#$%&'*+/=?^_`{|}~.-".contains(&byte);
    (1..=LOCAL_MAX_CHARS).contains(&local.len())
        && local.bytes().all(atom)
        && !local.starts_with('.')
        && !local.ends_with('.')
        && !local.contains("..")
}

fn valid_domain(domain: &str) -> bool {
    let label = |label: &str| {
        (1..=LABEL_MAX_CHARS).contains(&label.len())
            && label
                .bytes()
                .all(|byte| byte.is_ascii_alphanumeric() || byte == b'-')
            && !label.starts_with('-')
            && !label.ends_with('-')
    };
    domain.contains('.') && domain.split('.').all(label)
}

#[cfg(test)]
mod tests {
    use super::{Email, KindleEmail};

    #[test]
    fn accepts_plain_addresses_and_lowercases() {
        let parsed = KindleEmail::parse("  Reader.One+k@Kindle.com ");
        assert_eq!(
            parsed.as_ref().map(KindleEmail::as_str),
            Ok("reader.one+k@kindle.com")
        );
    }

    const REFUSED: [&str; 14] = [
        "",
        "plain",
        "@kindle.com",
        "a@",
        "a@kindle",
        "a b@kindle.com",
        "a@@kindle.com",
        "a@-kindle.com",
        "a@kindle..com",
        ".a@kindle.com",
        "a.@kindle.com",
        "\"a\"@kindle.com",
        "a@kindle.com,b@kindle.com",
        "ä@kindle.com",
    ];

    #[test]
    fn refuses_everything_else() {
        let accepted: Vec<&str> = REFUSED
            .into_iter()
            .filter(|bad| KindleEmail::parse(bad).is_ok())
            .collect();
        assert!(accepted.is_empty(), "{accepted:?}");
        assert!(KindleEmail::parse("a\n@kindle.com").is_err());
    }

    #[test]
    fn an_account_address_follows_the_same_rules() {
        assert_eq!(
            Email::parse(" Me@Example.org ").as_ref().map(Email::as_str),
            Ok("me@example.org")
        );
        assert!(Email::parse("me@example").is_err());
    }

    #[test]
    fn refuses_overlong_addresses() {
        let local = "a".repeat(65);
        assert!(KindleEmail::parse(&format!("{local}@kindle.com")).is_err());
    }
}
