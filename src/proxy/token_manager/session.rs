//! Session Management for Sticky Account Binding
//! 
//! Manages the mapping between client sessions and accounts to maintain
//! cache coherence and consistent behavior across requests.

use dashmap::DashMap;
use std::sync::Arc;

/// Session fingerprint to account binding manager
pub struct SessionManager {
    /// Maps (quota_group::session_id) -> account_id
    bindings: Arc<DashMap<String, String>>,
}

impl SessionManager {
    /// Create a new session manager
    pub fn new() -> Self {
        Self {
            bindings: Arc::new(DashMap::new()),
        }
    }

    /// Generate a session key from quota group and session ID
    pub fn session_key(quota_group: &str, session_id: &str) -> String {
        format!("{}::{}", quota_group, session_id)
    }

    /// Get the bound account for a session
    pub fn get_binding(&self, quota_group: &str, session_id: &str) -> Option<String> {
        let key = Self::session_key(quota_group, session_id);
        self.bindings.get(&key).map(|v| v.clone())
    }

    /// Bind a session to an account
    pub fn set_binding(&self, quota_group: &str, session_id: &str, account_id: &str) {
        let key = Self::session_key(quota_group, session_id);
        self.bindings.insert(key, account_id.to_string());
    }

    /// Remove a session binding
    pub fn remove_binding(&self, quota_group: &str, session_id: &str) -> bool {
        let key = Self::session_key(quota_group, session_id);
        self.bindings.remove(&key).is_some()
    }

    /// Clear all session bindings
    pub fn clear_all(&self) {
        self.bindings.clear();
    }

    /// Get the number of active bindings
    pub fn len(&self) -> usize {
        self.bindings.len()
    }

    /// Check if there are no bindings
    pub fn is_empty(&self) -> bool {
        self.bindings.is_empty()
    }
}

impl Default for SessionManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_session_binding() {
        let manager = SessionManager::new();
        
        // Initially empty
        assert!(manager.is_empty());
        
        // Set binding
        manager.set_binding("claude", "session-123", "account-456");
        assert_eq!(manager.len(), 1);
        
        // Get binding
        let bound = manager.get_binding("claude", "session-123");
        assert_eq!(bound, Some("account-456".to_string()));
        
        // Non-existent binding
        let none = manager.get_binding("gemini", "session-123");
        assert!(none.is_none());
    }

    #[test]
    fn test_remove_binding() {
        let manager = SessionManager::new();
        
        manager.set_binding("claude", "session-123", "account-456");
        assert_eq!(manager.len(), 1);
        
        // Remove binding
        let removed = manager.remove_binding("claude", "session-123");
        assert!(removed);
        assert!(manager.is_empty());
        
        // Remove non-existent
        let not_removed = manager.remove_binding("claude", "session-123");
        assert!(!not_removed);
    }

    #[test]
    fn test_clear_all() {
        let manager = SessionManager::new();
        
        manager.set_binding("claude", "session-1", "account-1");
        manager.set_binding("claude", "session-2", "account-2");
        manager.set_binding("gemini", "session-3", "account-3");
        assert_eq!(manager.len(), 3);
        
        manager.clear_all();
        assert!(manager.is_empty());
    }

    #[test]
    fn test_session_key_format() {
        let key = SessionManager::session_key("claude", "session-abc");
        assert_eq!(key, "claude::session-abc");
    }

    #[test]
    fn test_overwrite_binding() {
        let manager = SessionManager::new();
        
        manager.set_binding("claude", "session-1", "account-old");
        assert_eq!(
            manager.get_binding("claude", "session-1"),
            Some("account-old".to_string())
        );
        
        // Overwrite with new account
        manager.set_binding("claude", "session-1", "account-new");
        assert_eq!(
            manager.get_binding("claude", "session-1"),
            Some("account-new".to_string())
        );
        
        // Should still be just 1 binding
        assert_eq!(manager.len(), 1);
    }
}
