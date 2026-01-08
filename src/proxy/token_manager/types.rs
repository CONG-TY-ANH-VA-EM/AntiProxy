//! Shared types for token management

use std::path::PathBuf;

/// Represents a complete OAuth token with account metadata
#[derive(Debug, Clone)]
pub struct ProxyToken {
    pub account_id: String,
    pub access_token: String,
    pub refresh_token: String,
    pub expires_in: i64,
    pub timestamp: i64,
    pub email: String,
    pub account_path: PathBuf,
    pub project_id: Option<String>,
    pub subscription_tier: Option<String>, // "FREE" | "PRO" | "ULTRA"
}

/// Token selected for a specific request
#[derive(Debug, Clone)]
pub struct SelectedToken {
    pub access_token: String,
    pub project_id: String,
    pub email: String,
    pub account_id: String,
}

impl ProxyToken {
    /// Check if token is expired (with 5-minute buffer)
    pub fn is_expired(&self) -> bool {
        let now = chrono::Utc::now().timestamp();
        now >= self.timestamp - 300
    }

    /// Get subscription tier priority (lower is better)
    pub fn tier_priority(&self) -> u8 {
        match self.subscription_tier.as_deref() {
            Some("ULTRA") => 0,
            Some("PRO") => 1,
            Some("FREE") => 2,
            _ => 3,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_token_expiry() {
        let now = chrono::Utc::now().timestamp();
        
        let expired_token = ProxyToken {
            account_id: "test".to_string(),
            access_token: "token".to_string(),
            refresh_token: "refresh".to_string(),
            expires_in: 3600,
            timestamp: now - 400, // Expired 100 seconds ago (within 5-min buffer)
            email: "test@example.com".to_string(),
            account_path: PathBuf::from("/tmp/test.json"),
            project_id: None,
            subscription_tier: None,
        };

        assert!(expired_token.is_expired());

        let valid_token = ProxyToken {
            timestamp: now + 600, // Expires in 10 minutes
            ..expired_token
        };

        assert!(!valid_token.is_expired());
    }

    #[test]
    fn test_tier_priority() {
        let ultra = ProxyToken {
            account_id: "ultra".to_string(),
            access_token: "token".to_string(),
            refresh_token: "refresh".to_string(),
            expires_in: 3600,
            timestamp: chrono::Utc::now().timestamp() + 3600,
            email: "ultra@example.com".to_string(),
            account_path: PathBuf::from("/tmp/ultra.json"),
            project_id: None,
            subscription_tier: Some("ULTRA".to_string()),
        };

        let pro = ProxyToken {
            subscription_tier: Some("PRO".to_string()),
            ..ultra.clone()
        };

        let free = ProxyToken {
            subscription_tier: Some("FREE".to_string()),
            ..ultra.clone()
        };

        assert!(ultra.tier_priority() < pro.tier_priority());
        assert!(pro.tier_priority() < free.tier_priority());
    }
}
