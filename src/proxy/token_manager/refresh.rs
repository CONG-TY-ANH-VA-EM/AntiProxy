//! OAuth Token Refresh Module
//! 
//! Handles token refresh with concurrent protection to prevent
//! multiple simultaneous refreshes for the same account.

use dashmap::DashMap;
use std::sync::Arc;
use tokio::sync::Mutex;

use super::types::ProxyToken;

/// OAuth token response from Google
#[derive(Debug, Clone)]
pub struct TokenResponse {
    pub access_token: String,
    pub expires_in: i64,
}

/// Token refresh coordinator with per-account locking
pub struct RefreshCoordinator {
    /// Per-account refresh locks to prevent concurrent refreshes
    refresh_locks: Arc<DashMap<String, Arc<Mutex<()>>>>,
}

impl RefreshCoordinator {
    /// Create a new refresh coordinator
    pub fn new() -> Self {
        Self {
            refresh_locks: Arc::new(DashMap::new()),
        }
    }

    /// Get or create a refresh lock for an account
    pub fn get_lock(&self, account_id: &str) -> Arc<Mutex<()>> {
        self.refresh_locks
            .entry(account_id.to_string())
            .or_insert_with(|| Arc::new(Mutex::new(())))
            .clone()
    }

    /// Refresh a token, respecting the lock to prevent concurrent refreshes
    /// 
    /// Returns the new token response if refresh was successful,
    /// or an error message if refresh failed.
    pub async fn refresh_token(
        &self,
        token: &ProxyToken,
    ) -> Result<TokenResponse, String> {
        // Acquire lock for this account
        let lock = self.get_lock(&token.account_id);
        let _guard = lock.lock().await;

        // Check if token still needs refresh (might have been refreshed by another request)
        if !token.is_expired() {
            return Err("Token no longer needs refresh".to_string());
        }

        // Call OAuth refresh
        crate::modules::oauth::refresh_access_token(&token.refresh_token)
            .await
            .map(|response| TokenResponse {
                access_token: response.access_token,
                expires_in: response.expires_in,
            })
            .map_err(|e| e.to_string())
    }

    /// Update a token in storage after refresh
    pub async fn save_refreshed_token(
        token: &ProxyToken,
        response: &TokenResponse,
    ) -> Result<(), String> {
        use tokio::task::spawn_blocking;

        let path = token.account_path.clone();
        let content_str = {
            let path_clone = path.clone();
            spawn_blocking(move || std::fs::read_to_string(&path_clone))
                .await
                .map_err(|e| format!("Task failed: {}", e))?
                .map_err(|e| format!("Failed to read file: {}", e))?
        };

        let mut content: serde_json::Value = serde_json::from_str(&content_str)
            .map_err(|e| format!("Failed to parse JSON: {}", e))?;

        let now = chrono::Utc::now().timestamp();

        content["token"]["access_token"] = serde_json::Value::String(response.access_token.clone());
        content["token"]["expires_in"] = serde_json::Value::Number(response.expires_in.into());
        content["token"]["expiry_timestamp"] = serde_json::Value::Number((now + response.expires_in).into());

        let json_str = serde_json::to_string_pretty(&content)
            .map_err(|e| format!("Failed to serialize JSON: {}", e))?;
        
        let path_clone = path.clone();
        spawn_blocking(move || std::fs::write(&path_clone, json_str))
            .await
            .map_err(|e| format!("Task failed: {}", e))?
            .map_err(|e| format!("Failed to write file: {}", e))?;

        tracing::debug!("Saved refreshed token for account {}", token.account_id);
        Ok(())
    }

    /// Check if a refresh error indicates the account should be disabled
    pub fn is_permanent_error(error: &str) -> bool {
        error.contains("\"invalid_grant\"") || error.contains("invalid_grant")
    }
}

impl Default for RefreshCoordinator {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn create_test_token() -> ProxyToken {
        let now = chrono::Utc::now().timestamp();
        ProxyToken {
            account_id: "test-account".to_string(),
            access_token: "old-token".to_string(),
            refresh_token: "refresh-token".to_string(),
            expires_in: 3600,
            timestamp: now - 400, // Expired
            email: "test@example.com".to_string(),
            account_path: PathBuf::from("/tmp/test-account.json"),
            project_id: Some("project-123".to_string()),
            subscription_tier: Some("PRO".to_string()),
        }
    }

    #[test]
    fn test_lock_creation() {
        let coordinator = RefreshCoordinator::new();
        
        let lock1 = coordinator.get_lock("account-1");
        let lock2 = coordinator.get_lock("account-1");
        let lock3 = coordinator.get_lock("account-2");

        // Same account should get the same lock (via Arc pointer comparison)
        assert!(Arc::ptr_eq(&lock1, &lock2));
        
        // Different accounts get different locks
        assert!(!Arc::ptr_eq(&lock1, &lock3));
    }

    #[test]
    fn test_permanent_error_detection() {
        assert!(RefreshCoordinator::is_permanent_error("Error: \"invalid_grant\""));
        assert!(RefreshCoordinator::is_permanent_error("invalid_grant: token revoked"));
        assert!(!RefreshCoordinator::is_permanent_error("temporary network error"));
        assert!(!RefreshCoordinator::is_permanent_error("rate limit exceeded"));
    }

    #[test]
    fn test_token_expired_check() {
        let expired_token = create_test_token();
        assert!(expired_token.is_expired());

        let valid_token = ProxyToken {
            timestamp: chrono::Utc::now().timestamp() + 600,
            ..expired_token
        };
        assert!(!valid_token.is_expired());
    }
}
