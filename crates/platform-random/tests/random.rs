use platform_random::{OsRandom, RandomError, RandomSource, SequenceRandom, random_hex};

#[test]
fn os_randomness_fills_the_buffer_and_differs_between_calls() -> Result<(), RandomError> {
    let (mut first, mut second) = ([0u8; 32], [0u8; 32]);
    OsRandom.fill(&mut first)?;
    OsRandom.fill(&mut second)?;
    assert_ne!(first, [0u8; 32]);
    assert_ne!(first, second);
    Ok(())
}

#[test]
fn the_sequence_source_is_deterministic() -> Result<(), RandomError> {
    let source = SequenceRandom::default();
    assert_eq!(random_hex(&source, 4)?, "00010203");
    assert_eq!(random_hex(&source, 2)?, "0405");
    Ok(())
}

#[test]
fn hex_output_has_two_characters_per_byte() -> Result<(), RandomError> {
    assert_eq!(random_hex(&OsRandom, 32)?.len(), 64);
    Ok(())
}

#[test]
fn uuid_v7_has_the_version_variant_and_timestamp_and_sorts_by_time() -> Result<(), RandomError> {
    let early = platform_random::uuid_v7(1_700_000_000_000, &OsRandom)?;
    let late = platform_random::uuid_v7(1_800_000_000_000, &OsRandom)?;
    assert_eq!(early.get_version_num(), 7);
    assert_eq!(early.get_variant(), uuid::Variant::RFC4122);
    assert!(early < late, "ids sort by creation time");
    let millis = u64::from_be_bytes([
        0,
        0,
        early.as_bytes()[0],
        early.as_bytes()[1],
        early.as_bytes()[2],
        early.as_bytes()[3],
        early.as_bytes()[4],
        early.as_bytes()[5],
    ]);
    assert_eq!(millis, 1_700_000_000_000);
    Ok(())
}
