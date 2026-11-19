use std::time::Duration;

use platform_service_token::{
    IssueRequest, KeyId, KeyOwner, KeyRing, MAX_LIFETIME, ServiceName, SigningKey, TokenError,
    TokenIssuer, Verifier, bearer_token,
};
use platform_time::Instant;

type Failure = Box<dyn std::error::Error>;

fn name(text: &str) -> Result<ServiceName, TokenError> {
    ServiceName::parse(text)
}

fn key(fill: u8) -> Result<SigningKey, TokenError> {
    SigningKey::new(vec![fill; 32])
}

fn at(seconds: i64) -> Result<Instant, Failure> {
    Instant::from_unix_seconds(seconds).ok_or_else(|| "bad instant".into())
}

struct Setup {
    issuer: TokenIssuer,
    verifier: Verifier,
    callee: ServiceName,
}

fn setup() -> Result<Setup, Failure> {
    let (reader, identity) = (name("reader")?, name("identity")?);
    let issuer = TokenIssuer::new(reader.clone(), KeyId(1), key(7)?);
    let ring = KeyRing::default().with(
        KeyOwner {
            service: reader,
            id: KeyId(1),
        },
        key(7)?,
    );
    Ok(Setup {
        issuer,
        verifier: Verifier::new(identity.clone(), ring),
        callee: identity,
    })
}

fn issue(setup: &Setup, now: i64, lifetime: Duration) -> Result<String, Failure> {
    let request = IssueRequest {
        callee: &setup.callee,
        now: at(now)?,
        lifetime,
    };
    Ok(setup
        .issuer
        .issue(request)
        .ok_or("overflow")?
        .as_str()
        .to_owned())
}

#[test]
fn a_fresh_token_verifies_and_names_its_caller() -> Result<(), Failure> {
    let setup = setup()?;
    let token = issue(&setup, 1_000, Duration::from_secs(30))?;
    assert_eq!(
        setup.verifier.verify(&token, at(1_010)?)?.as_str(),
        "reader"
    );
    Ok(())
}

#[test]
fn expired_future_and_overlong_tokens_are_rejected() -> Result<(), Failure> {
    let setup = setup()?;
    let token = issue(&setup, 1_000, Duration::from_secs(30))?;
    assert_eq!(
        setup.verifier.verify(&token, at(1_031)?),
        Err(TokenError::Expired)
    );
    assert_eq!(
        setup.verifier.verify(&token, at(990)?),
        Err(TokenError::NotYetValid)
    );
    assert_eq!(
        setup.verifier.verify(&token, at(996)?).map(|_| ()),
        Ok(()),
        "within clock skew"
    );
    let long = issue(&setup, 1_000, MAX_LIFETIME + Duration::from_secs(1))?;
    assert_eq!(
        setup.verifier.verify(&long, at(1_001)?),
        Err(TokenError::LifetimeTooLong)
    );
    Ok(())
}

#[test]
fn tampering_with_any_field_breaks_the_signature() -> Result<(), Failure> {
    let setup = setup()?;
    let token = issue(&setup, 1_000, Duration::from_secs(30))?;
    let forged = token.replacen("1030", "9999", 1);
    assert_eq!(
        setup.verifier.verify(&forged, at(1_001)?),
        Err(TokenError::BadSignature)
    );
    let other_caller = token.replacen(".reader.", ".catalog.", 1);
    assert_eq!(
        setup.verifier.verify(&other_caller, at(1_001)?),
        Err(TokenError::UnknownKey)
    );
    Ok(())
}

#[test]
fn a_token_for_another_service_is_refused() -> Result<(), Failure> {
    let setup = setup()?;
    let request = IssueRequest {
        callee: &name("catalog")?,
        now: at(1_000)?,
        lifetime: Duration::from_secs(30),
    };
    let token = setup.issuer.issue(request).ok_or("overflow")?;
    assert_eq!(
        setup.verifier.verify(token.as_str(), at(1_001)?),
        Err(TokenError::WrongCallee)
    );
    Ok(())
}

#[test]
fn the_wrong_key_does_not_verify() -> Result<(), Failure> {
    let setup = setup()?;
    let ring = KeyRing::default().with(
        KeyOwner {
            service: name("reader")?,
            id: KeyId(1),
        },
        key(8)?,
    );
    let verifier = Verifier::new(name("identity")?, ring);
    let token = issue(&setup, 1_000, Duration::from_secs(30))?;
    assert_eq!(
        verifier.verify(&token, at(1_001)?),
        Err(TokenError::BadSignature)
    );
    Ok(())
}

#[test]
fn malformed_input_is_rejected_not_panicked_on() -> Result<(), Failure> {
    let setup = setup()?;
    for garbage in [
        "",
        "v1",
        "a.b.c",
        "v2.1.reader.identity.1.2.00",
        "v1.x.reader.identity.1.2.zz",
        ".....",
    ] {
        assert_eq!(
            setup.verifier.verify(garbage, at(1)?),
            Err(TokenError::Malformed),
            "{garbage:?}"
        );
    }
    Ok(())
}

#[test]
fn keys_and_names_are_validated_and_secrets_are_redacted() -> Result<(), Failure> {
    assert_eq!(
        SigningKey::new(vec![1; 31]).map(|_| ()),
        Err(TokenError::KeyTooShort)
    );
    assert_eq!(ServiceName::parse("Bad.Name"), Err(TokenError::InvalidName));
    assert_eq!(ServiceName::parse(""), Err(TokenError::InvalidName));
    assert!(!format!("{:?}", key(9)?).contains('9'));
    assert_eq!(bearer_token("Service abc"), Some("abc"));
    assert_eq!(bearer_token("Bearer abc"), None);
    Ok(())
}
