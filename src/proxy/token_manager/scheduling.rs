//! Account Scheduling Algorithms
//! 
//! Implements intelligent account selection based on:
//! - Subscription tier prioritization (ULTRA > PRO > FREE)
//! - Rate limit avoidance
//! - Session stickiness
//! - Round-robin load balancing

use std::collections::HashSet;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;

use dashmap::DashMap;

use super::types::ProxyToken;
use crate::proxy::rate_limit::RateLimitTracker;
use crate::proxy::sticky_config::{SchedulingMode, StickySessionConfig};

/// Scheduling decision result
#[derive(Debug, Clone)]
pub enum SchedulingDecision {
    /// Use this account immediately
    UseAccount(ProxyToken),
    /// Wait for rate limit to clear, then use account
    WaitAndUse { token: ProxyToken, wait_seconds: u64 },
    /// All accounts are unavailable
    AllUnavailable { min_wait_seconds: u64 },
}

/// Account scheduler with multiple selection strategies
pub struct AccountScheduler {
    /// Round-robin index per quota group
    round_robin_index: Arc<DashMap<String, Arc<AtomicUsize>>>,
    /// Rate limit tracker reference
    rate_limit_tracker: Arc<RateLimitTracker>,
}

impl AccountScheduler {
    /// Create a new account scheduler
    pub fn new(rate_limit_tracker: Arc<RateLimitTracker>) -> Self {
        Self {
            round_robin_index: Arc::new(DashMap::new()),
            rate_limit_tracker,
        }
    }

    /// Generate scope group key from quota group and request type
    pub fn scope_group(quota_group: &str, request_type: &str) -> String {
        if request_type == "image_gen" {
            format!("{}::image_gen", quota_group)
        } else {
            quota_group.to_string()
        }
    }

    /// Sort tokens by subscription tier priority (ULTRA first, FREE last)
    pub fn sort_by_tier(tokens: &mut [ProxyToken]) {
        tokens.sort_by(|a, b| a.tier_priority().cmp(&b.tier_priority()));
    }

    /// Get the next round-robin index for a quota group
    fn get_next_index(&self, scope_group: &str, total: usize) -> usize {
        let counter = self
            .round_robin_index
            .entry(scope_group.to_string())
            .or_insert_with(|| Arc::new(AtomicUsize::new(0)))
            .clone();
        
        counter.fetch_add(1, Ordering::SeqCst) % total
    }

    /// Select an account using round-robin with rate limit avoidance
    pub fn select_round_robin(
        &self,
        tokens: &[ProxyToken],
        scope_group: &str,
        attempted: &HashSet<String>,
    ) -> Option<ProxyToken> {
        let total = tokens.len();
        if total == 0 {
            return None;
        }

        let start_idx = self.get_next_index(scope_group, total);
        
        for offset in 0..total {
            let idx = (start_idx + offset) % total;
            let candidate = &tokens[idx];
            
            // Skip already attempted accounts
            if attempted.contains(&candidate.account_id) {
                continue;
            }
            
            // Skip rate-limited accounts
            if self.rate_limit_tracker.is_rate_limited(scope_group, &candidate.account_id) {
                continue;
            }
            
            return Some(candidate.clone());
        }
        
        None
    }

    /// Select account with sticky session support
    pub fn select_with_session(
        &self,
        tokens: &[ProxyToken],
        scope_group: &str,
        bound_account_id: Option<&str>,
        scheduling: &StickySessionConfig,
        attempted: &HashSet<String>,
    ) -> SchedulingDecision {
        // If we have a bound account, try to use it
        if let Some(bound_id) = bound_account_id {
            // Check if bound account is rate limited
            let remaining_wait = self
                .rate_limit_tracker
                .get_remaining_wait(scope_group, bound_id);

            if remaining_wait > 0 {
                // Account is rate limited
                match scheduling.mode {
                    SchedulingMode::CacheFirst if remaining_wait <= scheduling.max_wait_seconds => {
                        // Wait for bound account to become available
                        if let Some(token) = tokens.iter().find(|t| t.account_id == bound_id) {
                            return SchedulingDecision::WaitAndUse {
                                token: token.clone(),
                                wait_seconds: remaining_wait,
                            };
                        }
                    }
                    _ => {
                        // Switch to a different account
                        tracing::debug!(
                            "Session bound account {} is rate limited for {}s, switching",
                            bound_id, remaining_wait
                        );
                    }
                }
            } else if !attempted.contains(bound_id) {
                // Bound account is available and not previously attempted
                if let Some(token) = tokens.iter().find(|t| t.account_id == bound_id) {
                    return SchedulingDecision::UseAccount(token.clone());
                }
            }
        }

        // Fall back to round-robin selection
        match self.select_round_robin(tokens, scope_group, attempted) {
            Some(token) => SchedulingDecision::UseAccount(token),
            None => {
                // Calculate minimum wait time across all accounts
                let min_wait = tokens
                    .iter()
                    .filter_map(|t| {
                        self.rate_limit_tracker
                            .get_reset_seconds(scope_group, &t.account_id)
                    })
                    .min()
                    .unwrap_or(60);

                SchedulingDecision::AllUnavailable {
                    min_wait_seconds: min_wait,
                }
            }
        }
    }

    /// Get all healthy (non-rate-limited) accounts
    pub fn get_healthy_accounts<'a>(
        &self,
        tokens: &'a [ProxyToken],
        scope_group: &str,
    ) -> Vec<&'a ProxyToken> {
        tokens
            .iter()
            .filter(|t| !self.rate_limit_tracker.is_rate_limited(scope_group, &t.account_id))
            .collect()
    }

    /// Get the count of rate-limited accounts
    pub fn count_limited_accounts(&self, tokens: &[ProxyToken], scope_group: &str) -> usize {
        tokens
            .iter()
            .filter(|t| self.rate_limit_tracker.is_rate_limited(scope_group, &t.account_id))
            .count()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn create_test_tokens() -> Vec<ProxyToken> {
        let now = chrono::Utc::now().timestamp() + 3600;
        vec![
            ProxyToken {
                account_id: "ultra-1".to_string(),
                access_token: "token".to_string(),
                refresh_token: "refresh".to_string(),
                expires_in: 3600,
                timestamp: now,
                email: "ultra@example.com".to_string(),
                account_path: PathBuf::from("/tmp/ultra.json"),
                project_id: Some("proj".to_string()),
                subscription_tier: Some("ULTRA".to_string()),
            },
            ProxyToken {
                account_id: "pro-1".to_string(),
                subscription_tier: Some("PRO".to_string()),
                email: "pro@example.com".to_string(),
                account_path: PathBuf::from("/tmp/pro.json"),
                ..create_base_token(now)
            },
            ProxyToken {
                account_id: "free-1".to_string(),
                subscription_tier: Some("FREE".to_string()),
                email: "free@example.com".to_string(),
                account_path: PathBuf::from("/tmp/free.json"),
                ..create_base_token(now)
            },
        ]
    }

    fn create_base_token(timestamp: i64) -> ProxyToken {
        ProxyToken {
            account_id: "base".to_string(),
            access_token: "token".to_string(),
            refresh_token: "refresh".to_string(),
            expires_in: 3600,
            timestamp,
            email: "base@example.com".to_string(),
            account_path: PathBuf::from("/tmp/base.json"),
            project_id: Some("proj".to_string()),
            subscription_tier: None,
        }
    }

    #[test]
    fn test_tier_sorting() {
        let mut tokens = create_test_tokens();
        // Shuffle order
        tokens.reverse();
        
        AccountScheduler::sort_by_tier(&mut tokens);
        
        assert_eq!(tokens[0].subscription_tier.as_deref(), Some("ULTRA"));
        assert_eq!(tokens[1].subscription_tier.as_deref(), Some("PRO"));
        assert_eq!(tokens[2].subscription_tier.as_deref(), Some("FREE"));
    }

    #[test]
    fn test_scope_group_generation() {
        assert_eq!(
            AccountScheduler::scope_group("claude", "chat"),
            "claude"
        );
        assert_eq!(
            AccountScheduler::scope_group("claude", "image_gen"),
            "claude::image_gen"
        );
    }

    #[test]
    fn test_round_robin_selection() {
        let tracker = Arc::new(RateLimitTracker::new());
        let scheduler = AccountScheduler::new(tracker);
        let tokens = create_test_tokens();
        let attempted = HashSet::new();

        // First selection
        let first = scheduler.select_round_robin(&tokens, "claude", &attempted);
        assert!(first.is_some());

        // Second selection should pick a different account
        let second = scheduler.select_round_robin(&tokens, "claude", &attempted);
        assert!(second.is_some());

        // Third selection
        let third = scheduler.select_round_robin(&tokens, "claude", &attempted);
        assert!(third.is_some());
    }

    #[test]
    fn test_skip_attempted_accounts() {
        let tracker = Arc::new(RateLimitTracker::new());
        let scheduler = AccountScheduler::new(tracker);
        let tokens = create_test_tokens();
        
        let mut attempted = HashSet::new();
        attempted.insert("ultra-1".to_string());
        attempted.insert("pro-1".to_string());

        let selected = scheduler.select_round_robin(&tokens, "claude", &attempted);
        assert!(selected.is_some());
        assert_eq!(selected.unwrap().account_id, "free-1");
    }

    #[test]
    fn test_all_accounts_attempted() {
        let tracker = Arc::new(RateLimitTracker::new());
        let scheduler = AccountScheduler::new(tracker);
        let tokens = create_test_tokens();
        
        let mut attempted = HashSet::new();
        for token in &tokens {
            attempted.insert(token.account_id.clone());
        }

        let selected = scheduler.select_round_robin(&tokens, "claude", &attempted);
        assert!(selected.is_none());
    }

    #[test]
    fn test_scheduling_decision_use_account() {
        let tracker = Arc::new(RateLimitTracker::new());
        let scheduler = AccountScheduler::new(tracker);
        let tokens = create_test_tokens();
        let config = StickySessionConfig::default();
        let attempted = HashSet::new();

        let decision = scheduler.select_with_session(
            &tokens,
            "claude",
            Some("ultra-1"),
            &config,
            &attempted,
        );

        match decision {
            SchedulingDecision::UseAccount(token) => {
                assert_eq!(token.account_id, "ultra-1");
            }
            _ => panic!("Expected UseAccount decision"),
        }
    }

    #[test]
    fn test_empty_token_pool() {
        let tracker = Arc::new(RateLimitTracker::new());
        let scheduler = AccountScheduler::new(tracker);
        let tokens: Vec<ProxyToken> = vec![];
        let attempted = HashSet::new();

        let selected = scheduler.select_round_robin(&tokens, "claude", &attempted);
        assert!(selected.is_none());
    }

    #[test]
    fn test_healthy_accounts_count() {
        let tracker = Arc::new(RateLimitTracker::new());
        let scheduler = AccountScheduler::new(tracker.clone());
        let tokens = create_test_tokens();

        // Initially all healthy
        let healthy = scheduler.get_healthy_accounts(&tokens, "claude");
        assert_eq!(healthy.len(), 3);

        // Mark one as rate limited
        tracker.mark_limited("claude", "ultra-1", 60);

        let healthy = scheduler.get_healthy_accounts(&tokens, "claude");
        assert_eq!(healthy.len(), 2);

        let limited = scheduler.count_limited_accounts(&tokens, "claude");
        assert_eq!(limited, 1);
    }
}
