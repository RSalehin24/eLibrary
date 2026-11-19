use contracts_ids::{BookId, InvalidId, UserId};
use uuid::Uuid;

const SAMPLE: &str = "67e55044-10b1-426f-9247-bb680e5fe0c8";

#[test]
fn id_round_trips_through_text() -> Result<(), InvalidId> {
    let id: BookId = SAMPLE.parse()?;
    assert_eq!(id.to_string(), SAMPLE);
    Ok(())
}

#[test]
fn garbage_is_rejected() {
    assert_eq!("not-a-uuid".parse::<UserId>(), Err(InvalidId));
}

#[test]
fn id_serializes_as_a_bare_string() -> Result<(), serde_json::Error> {
    let id = UserId::from_uuid(Uuid::nil());
    assert_eq!(
        serde_json::to_string(&id)?,
        "\"00000000-0000-0000-0000-000000000000\""
    );
    assert_eq!(
        serde_json::from_str::<UserId>("\"00000000-0000-0000-0000-000000000000\"")?,
        id
    );
    Ok(())
}
