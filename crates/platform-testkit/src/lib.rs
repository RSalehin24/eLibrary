//! Test helpers shared by the workspace. Database tests are `#[ignore]`d in a plain `cargo test`
//! and run by `cargo xtask check` (gate Q4) against the throwaway Postgres of `compose.test.yaml`.

mod database;

pub use database::{TestDatabase, TestkitError};
