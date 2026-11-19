use domain_credentials::{
    Attempt, PASSWORD_MAX_CHARS, Password, PasswordError, PasswordHash, SALT_BYTES, TotpError,
    TotpSecret, TotpStep, verify_code,
};
use platform_time::Instant;
use proptest::prelude::*;

type Failure = Box<dyn std::error::Error>;

const RFC_SECRET: &[u8] = b"12345678901234567890";

fn secret() -> Result<TotpSecret, TotpError> {
    TotpSecret::from_bytes(RFC_SECRET.to_vec())
}

fn check(
    code: &str,
    seconds: i64,
    last_accepted: Option<TotpStep>,
) -> Result<Result<TotpStep, TotpError>, Failure> {
    let attempt = Attempt {
        code,
        now: at(seconds)?,
        last_accepted,
    };
    Ok(verify_code(&secret()?, attempt))
}

fn at(seconds: i64) -> Result<Instant, Failure> {
    Instant::from_unix_seconds(seconds).ok_or_else(|| "bad instant".into())
}

#[test]
fn hotp_matches_the_rfc_4226_vectors() -> Result<(), Failure> {
    let expected = [
        755_224, 287_082, 359_152, 969_429, 338_314, 254_676, 287_922, 162_583, 399_871, 520_489,
    ];
    for (counter, code) in expected.into_iter().enumerate() {
        assert_eq!(
            secret()?.code_for(TotpStep(u64::try_from(counter)?)),
            code,
            "counter {counter}"
        );
    }
    Ok(())
}

#[test]
fn totp_matches_the_rfc_6238_vectors() -> Result<(), Failure> {
    let vectors = [
        (59, "287082"),
        (1_111_111_109, "081804"),
        (1_111_111_111, "050471"),
        (1_234_567_890, "005924"),
        (2_000_000_000, "279037"),
        (20_000_000_000, "353130"),
    ];
    for (seconds, code) in vectors {
        assert_eq!(
            verify_code(
                &secret()?,
                Attempt {
                    code,
                    now: at(seconds)?,
                    last_accepted: None
                }
            ),
            Ok(TotpStep(u64::try_from(seconds / 30)?)),
            "{seconds}"
        );
    }
    Ok(())
}

#[test]
fn drift_of_one_step_is_accepted_two_is_not() -> Result<(), Failure> {
    let code = "287082"; // step 1 (t = 30..59)
    assert!(
        verify_code(
            &secret()?,
            Attempt {
                code,
                now: at(89)?,
                last_accepted: None
            }
        )
        .is_ok(),
        "one step late"
    );
    assert_eq!(
        verify_code(
            &secret()?,
            Attempt {
                code,
                now: at(120)?,
                last_accepted: None
            }
        ),
        Err(TotpError::InvalidCode)
    );
    Ok(())
}

#[test]
fn a_used_step_and_older_steps_are_replays() -> Result<(), Failure> {
    let accepted = check("287082", 59, None)??;
    assert_eq!(
        check("287082", 59, Some(accepted))?,
        Err(TotpError::Replayed)
    );
    assert_eq!(
        check("287082", 59, Some(TotpStep(accepted.0 + 5)))?,
        Err(TotpError::Replayed)
    );
    Ok(())
}

#[test]
fn malformed_codes_are_invalid_not_panics() -> Result<(), Failure> {
    for code in ["", "12345", "1234567", "12345a", "２８７０８２", " 287082"] {
        assert_eq!(
            verify_code(
                &secret()?,
                Attempt {
                    code,
                    now: at(59)?,
                    last_accepted: None
                }
            ),
            Err(TotpError::InvalidCode),
            "{code:?}"
        );
    }
    Ok(())
}

#[test]
fn secrets_round_trip_through_base32_and_are_redacted() -> Result<(), Failure> {
    assert_eq!(secret()?.to_base32(), "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ");
    assert_eq!(
        TotpSecret::from_base32("gezd gnbv gy3t qojq gezd gnbv gy3t qojq==")?,
        secret()?
    );
    assert_eq!(
        TotpSecret::from_base32("not base32!"),
        Err(TotpError::InvalidSecret)
    );
    assert_eq!(
        TotpSecret::from_bytes(vec![1; 15]),
        Err(TotpError::InvalidSecret)
    );
    assert!(!format!("{:?}", secret()?).contains("GEZD"));
    Ok(())
}

proptest! {
    #[test]
    fn base32_round_trips(bytes in proptest::collection::vec(any::<u8>(), 16..64)) {
        let secret = TotpSecret::from_bytes(bytes.clone());
        let again = secret.clone().and_then(|s| TotpSecret::from_base32(&s.to_base32()));
        prop_assert_eq!(again, secret);
    }

    #[test]
    fn verification_never_panics_and_only_accepts_the_right_code(code in "\\PC{0,8}", seconds in 0i64..4_000_000_000) {
        let secret = TotpSecret::from_bytes(RFC_SECRET.to_vec()).map_err(|e| TestCaseError::fail(e.to_string()))?;
        let now = Instant::from_unix_seconds(seconds).ok_or_else(|| TestCaseError::fail("instant"))?;
        if let Ok(step) = verify_code(&secret, Attempt { code: &code, now, last_accepted: None }) {
            prop_assert_eq!(format!("{:06}", secret.code_for(step)), code);
        }
    }
}

const SALT: [u8; SALT_BYTES] = [7; SALT_BYTES];

#[test]
fn password_policy_enforces_length_and_deny_list() -> Result<(), Failure> {
    assert_eq!(
        Password::parse("short").err(),
        Some(PasswordError::TooShort)
    );
    assert_eq!(
        Password::parse(&"x".repeat(PASSWORD_MAX_CHARS + 1)).err(),
        Some(PasswordError::TooLong)
    );
    assert_eq!(
        Password::parse("PassWord1234").err(),
        Some(PasswordError::TooCommon)
    );
    assert!(
        Password::parse("বাংলা-পাসওয়ার্ড-১২৩৪").is_ok(),
        "counted in characters, not bytes"
    );
    assert!(Password::parse(&"y".repeat(PASSWORD_MAX_CHARS)).is_ok());
    assert!(!format!("{:?}", Password::parse("correct horse battery")?).contains("horse"));
    Ok(())
}

#[test]
fn a_hash_verifies_the_password_and_nothing_else() -> Result<(), Failure> {
    let hash = PasswordHash::create(&Password::parse("correct horse battery")?, &SALT)?;
    assert!(hash.as_str().starts_with("$argon2id$"), "{}", hash.as_str());
    assert!(hash.verify("correct horse battery"));
    assert!(!hash.verify("correct horse batterz"));
    assert!(!hash.verify(""));
    assert_eq!(PasswordHash::from_stored(hash.as_str()), Some(hash.clone()));
    assert_eq!(PasswordHash::from_stored("not a hash"), None);
    assert!(!format!("{hash:?}").contains("argon2"));
    Ok(())
}

#[test]
fn different_salts_give_different_hashes_for_the_same_password() -> Result<(), Failure> {
    let password = Password::parse("correct horse battery")?;
    let first = PasswordHash::create(&password, &[1; SALT_BYTES])?;
    let second = PasswordHash::create(&password, &[2; SALT_BYTES])?;
    assert_ne!(first.as_str(), second.as_str());
    Ok(())
}
