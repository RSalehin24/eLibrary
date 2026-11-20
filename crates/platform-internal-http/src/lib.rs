//! Calls between our own services over internal HTTP: one shared client with timeouts, and
//! signed calls that carry a short-lived service token (D-101). Used by the gateway and by every
//! service that calls another.

mod client;
mod server;
mod signed;

pub use client::{Fault, UpstreamClient};
pub use server::{HasVerifier, Peer, PeerRejection};
pub use signed::{Caller, Reply, SignedCall};
