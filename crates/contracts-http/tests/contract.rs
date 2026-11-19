use std::collections::BTreeMap;

use contracts_http::{CommonErrorCode, ErrorClass, ErrorEnvelope, Page, Scope};

const CATALOG: &str = include_str!("../../../planning/07-contracts/error-catalog.md");

/// Codes and statuses from the two catalog sections every service shares.
fn catalog_codes() -> BTreeMap<String, u16> {
    let shared = CATALOG.split("\n## Identity").next().unwrap_or_default();
    shared.lines().filter_map(parse_row).collect()
}

fn parse_row(line: &str) -> Option<(String, u16)> {
    let cells: Vec<&str> = line.split('|').map(str::trim).collect();
    let code_at = cells.iter().position(|cell| cell.starts_with('`'))?;
    let code = cells.get(code_at)?.trim_matches('`').to_owned();
    let status = cells.iter().find_map(|cell| cell.parse::<u16>().ok())?;
    Some((code, status))
}

#[test]
fn codes_and_statuses_match_the_catalog_document() {
    let in_code: BTreeMap<String, u16> = CommonErrorCode::ALL
        .iter()
        .map(|code| (code.as_str().to_owned(), code.http_status()))
        .collect();
    let in_catalog = catalog_codes();
    assert!(
        in_catalog.len() >= 19,
        "catalog parse found {}",
        in_catalog.len()
    );
    assert_eq!(in_code, in_catalog);
}

#[test]
fn retry_class_follows_the_catalog() {
    assert_eq!(CommonErrorCode::RateLimited.class(), ErrorClass::Retryable);
    assert_eq!(CommonErrorCode::Timeout.class(), ErrorClass::Retryable);
    assert_eq!(CommonErrorCode::NotFound.class(), ErrorClass::Permanent);
}

#[test]
fn envelope_has_the_documented_shape_and_omits_absent_details() -> Result<(), serde_json::Error> {
    let envelope = ErrorEnvelope::new(CommonErrorCode::NotFound, "No such book", "req-1");
    let json = serde_json::to_value(&envelope)?;
    assert_eq!(
        json,
        serde_json::json!({"error": {"code": "not_found", "message": "No such book", "request_id": "req-1"}})
    );
    assert_eq!(serde_json::from_value::<ErrorEnvelope>(json)?, envelope);
    Ok(())
}

#[test]
fn scopes_use_snake_case_names() -> Result<(), serde_json::Error> {
    assert_eq!(serde_json::to_string(&Scope::ReadOnce)?, "\"read_once\"");
    assert_eq!(
        serde_json::from_str::<Scope>("\"manage_catalog\"")?,
        Scope::ManageCatalog
    );
    Ok(())
}

#[test]
fn page_round_trips_with_and_without_next() -> Result<(), serde_json::Error> {
    let page = Page {
        items: vec![1, 2],
        next: None,
    };
    let json = serde_json::to_string(&page)?;
    assert_eq!(json, r#"{"items":[1,2],"next":null}"#);
    assert_eq!(serde_json::from_str::<Page<i32>>(&json)?, page);
    Ok(())
}

#[test]
fn scope_names_match_the_wire_format_and_all_is_complete() -> Result<(), serde_json::Error> {
    for scope in Scope::ALL {
        assert_eq!(
            serde_json::to_string(&scope)?,
            format!("\"{}\"", scope.as_str())
        );
    }
    let names: std::collections::BTreeSet<&str> =
        Scope::ALL.iter().map(|scope| scope.as_str()).collect();
    assert_eq!(names.len(), Scope::ALL.len(), "scope names are unique");
    Ok(())
}
