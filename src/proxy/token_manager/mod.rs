//! Token Manager Module
//! 
//! Manages OAuth tokens, account rotation, and intelligent scheduling for multi-provider AI proxy.
//! 
//! # Architecture
//! 
//! - `core`: TokenManager struct and initialization
//! - `scheduling`: Account selection algorithms (sticky sessions, round-robin, health-based)
//! - `refresh`: OAuth token refresh with concurrent protection
//! - `session`: Session fingerprinting and sticky account binding
//! - `types`: Shared data structures

mod core;
mod scheduling;
mod refresh;
mod session;
mod types;

#[cfg(test)]
mod tests;

// Re-export public API
pub use core::TokenManager;
pub use types::{ProxyToken, SelectedToken};
