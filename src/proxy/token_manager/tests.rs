//! Integration Tests for Token Manager
//! 
//! Comprehensive tests covering account selection, session stickiness,
//! rate limit handling, and token refresh scenarios.

use super::*;
use std::path::PathBuf;

/// Helper to create a test token
fn create_test_token(id: &str, email: &str, tier: Option<&str>) -> types::ProxyToken {
    let now = chrono::Utc::now().timestamp() + 3600;
    types::ProxyToken {
        account_id: id.to_string(),
        access_token: format!("token-{}", id),
        refresh_token: format!("refresh-{}", id),
        expires_in: 3600,
        timestamp: now,
        email: email.to_string(),
        account_path: PathBuf::from(format!("/tmp/{}.json", id)),
        project_id: Some(format!("project-{}", id)),
        subscription_tier: tier.map(String::from),
    }
}

#[cfg(test)]
mod session_tests {
    use crate::proxy::token_manager::session::SessionManager;

    #[test]
    fn test_session_isolation_between_groups() {
        let manager = SessionManager::new();
        
        // Bind session to different accounts in different groups
        manager.set_binding("claude", "session-1", "claude-account");
        manager.set_binding("gemini", "session-1", "gemini-account");
        
        // Same session ID, different groups, different accounts
        assert_eq!(
            manager.get_binding("claude", "session-1"),
            Some("claude-account".to_string())
        );
        assert_eq!(
            manager.get_binding("gemini", "session-1"),
            Some("gemini-account".to_string())
        );
    }

    #[test]
    fn test_session_rebinding_after_rotation() {
        let manager = SessionManager::new();
        
        // Initial binding
        manager.set_binding("claude", "session-1", "account-A");
        
        // Simulate rotation - remove and rebind
        manager.remove_binding("claude", "session-1");
        manager.set_binding("claude", "session-1", "account-B");
        
        assert_eq!(
            manager.get_binding("claude", "session-1"),
            Some("account-B".to_string())
        );
    }
}

#[cfg(test)]
mod scheduling_tests {
    use super::*;
    use crate::proxy::rate_limit::RateLimitTracker;
    use crate::proxy::token_manager::scheduling::AccountScheduler;
    use std::collections::HashSet;
    use std::sync::Arc;

    #[test]
    fn test_tier_priority_ordering() {
        let mut tokens = vec![
            create_test_token("free-1", "free@test.com", Some("FREE")),
            create_test_token("ultra-1", "ultra@test.com", Some("ULTRA")),
            create_test_token("pro-1", "pro@test.com", Some("PRO")),
            create_test_token("unknown-1", "unknown@test.com", None),
        ];
        
        AccountScheduler::sort_by_tier(&mut tokens);
        
        // Order should be: ULTRA, PRO, FREE, Unknown
        assert_eq!(tokens[0].account_id, "ultra-1");
        assert_eq!(tokens[1].account_id, "pro-1");
        assert_eq!(tokens[2].account_id, "free-1");
        assert_eq!(tokens[3].account_id, "unknown-1");
    }

    #[test]
    fn test_round_robin_fairness() {
        let tracker = Arc::new(RateLimitTracker::new());
        let scheduler = AccountScheduler::new(tracker);
        
        let tokens = vec![
            create_test_token("a", "a@test.com", Some("PRO")),
            create_test_token("b", "b@test.com", Some("PRO")),
            create_test_token("c", "c@test.com", Some("PRO")),
        ];
        
        let attempted = HashSet::new();
        let mut selected_ids = Vec::new();
        
        // Select 6 times to see round-robin behavior
        for _ in 0..6 {
            if let Some(token) = scheduler.select_round_robin(&tokens, "test", &attempted) {
                selected_ids.push(token.account_id.clone());
            }
        }
        
        // Each account should be selected at least once
        assert!(selected_ids.contains(&"a".to_string()));
        assert!(selected_ids.contains(&"b".to_string()));
        assert!(selected_ids.contains(&"c".to_string()));
    }

    #[test]
    fn test_rate_limit_avoidance() {
        let tracker = Arc::new(RateLimitTracker::new());
        let scheduler = AccountScheduler::new(tracker.clone());
        
        let tokens = vec![
            create_test_token("healthy", "healthy@test.com", Some("PRO")),
            create_test_token("limited", "limited@test.com", Some("PRO")),
        ];
        
        // Mark one account as rate limited
        tracker.mark_limited("test", "limited", 60);
        
        let attempted = HashSet::new();
        
        // Should always select the healthy account
        for _ in 0..5 {
            let token = scheduler.select_round_robin(&tokens, "test", &attempted);
            assert!(token.is_some());
            assert_eq!(token.unwrap().account_id, "healthy");
        }
    }
}

#[cfg(test)]
mod refresh_tests {
    use super::*;
    use crate::proxy::token_manager::refresh::RefreshCoordinator;
    use std::sync::Arc;

    #[test]
    fn test_refresh_lock_per_account() {
        let coordinator = RefreshCoordinator::new();
        
        let lock_a1 = coordinator.get_lock("account-a");
        let lock_a2 = coordinator.get_lock("account-a");
        let lock_b = coordinator.get_lock("account-b");
        
        // Same account gets same lock
        assert!(Arc::ptr_eq(&lock_a1, &lock_a2));
        
        // Different accounts get different locks
        assert!(!Arc::ptr_eq(&lock_a1, &lock_b));
    }

    #[test]
    fn test_permanent_error_detection() {
        // These should be detected as permanent
        assert!(RefreshCoordinator::is_permanent_error(r#"{"error": "invalid_grant"}"#));
        assert!(RefreshCoordinator::is_permanent_error("invalid_grant: Token revoked"));
        
        // These should NOT be detected as permanent
        assert!(!RefreshCoordinator::is_permanent_error("rate_limit_exceeded"));
        assert!(!RefreshCoordinator::is_permanent_error("temporary_unavailable"));
        assert!(!RefreshCoordinator::is_permanent_error("network_timeout"));
    }

    #[test]
    fn test_token_expiry_buffer() {
        let now = chrono::Utc::now().timestamp();
        
        // Token expires in 4 minutes (within 5-min buffer) - should be considered expired
        let near_expiry = types::ProxyToken {
            account_id: "test".to_string(),
            access_token: "token".to_string(),
            refresh_token: "refresh".to_string(),
            expires_in: 3600,
            timestamp: now + 240, // 4 minutes from now
            email: "test@example.com".to_string(),
            account_path: PathBuf::from("/tmp/test.json"),
            project_id: None,
            subscription_tier: None,
        };
        
        assert!(near_expiry.is_expired()); // Within 5-min buffer
        
        // Token expires in 10 minutes - should NOT be considered expired
        let healthy = types::ProxyToken {
            timestamp: now + 600, // 10 minutes from now
            ..near_expiry
        };
        
        assert!(!healthy.is_expired());
    }
}

#[cfg(test)]
mod integration_tests {
    use super::*;
    use crate::proxy::token_manager::core::TokenManager;

    #[tokio::test]
    async fn test_manager_initialization() {
        let manager = TokenManager::new(PathBuf::from("/tmp/antiproxy-test"));
        
        assert!(manager.is_empty());
        assert_eq!(manager.len(), 0);
    }

    #[tokio::test]
    async fn test_scheduling_config_persistence() {
        use crate::proxy::sticky_config::{SchedulingMode, StickySessionConfig};
        
        let manager = TokenManager::new(PathBuf::from("/tmp/antiproxy-test"));
        
        // Default config from StickySessionConfig is CacheFirst with 120s
        let config = manager.get_sticky_config().await;
        assert_eq!(config.mode, SchedulingMode::CacheFirst);
        assert_eq!(config.max_wait_seconds, 120);
        
        // Update config to Balance mode with different wait time
        manager.update_sticky_config(StickySessionConfig {
            mode: SchedulingMode::Balance,
            max_wait_seconds: 60,
        }).await;
        
        let updated = manager.get_sticky_config().await;
        assert_eq!(updated.mode, SchedulingMode::Balance);
        assert_eq!(updated.max_wait_seconds, 60);
    }

    #[tokio::test]
    async fn test_rate_limit_tracking() {
        let manager = TokenManager::new(PathBuf::from("/tmp/antiproxy-test"));
        
        // Initially not rate limited
        assert!(!manager.is_rate_limited("claude", "chat", "account-1"));
        
        // Mark as rate limited
        manager.mark_rate_limited(
            "claude",
            "chat",
            "account-1",
            429,
            Some("60"),
            r#"{"error": "rate_limit_exceeded"}"#,
        );
        
        // Now should be rate limited
        assert!(manager.is_rate_limited("claude", "chat", "account-1"));
        
        // Different group should not be affected
        assert!(!manager.is_rate_limited("gemini", "chat", "account-1"));
    }

    #[tokio::test]
    async fn test_session_management() {
        let manager = TokenManager::new(PathBuf::from("/tmp/antiproxy-test"));
        
        // Test clear_all_sessions (public API)
        // Sessions are managed internally during get_token calls,
        // but we can verify the clear functionality works
        manager.clear_all_sessions();
        
        // Verify manager is still functional after clearing
        assert!(manager.is_empty());
    }
}
