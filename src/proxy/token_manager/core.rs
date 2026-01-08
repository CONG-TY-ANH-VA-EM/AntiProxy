//! Core TokenManager Implementation
//! 
//! The main TokenManager struct that coordinates account loading,
//! token selection, and refresh operations.

use dashmap::DashMap;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::RwLock;

use super::refresh::{RefreshCoordinator, TokenResponse};
use super::scheduling::{AccountScheduler, SchedulingDecision};
use super::session::SessionManager;
use super::types::{ProxyToken, SelectedToken};
use crate::proxy::rate_limit::RateLimitTracker;
use crate::proxy::sticky_config::StickySessionConfig;

/// Token Manager - the brain of the proxy's account rotation system
/// 
/// Manages multiple Google accounts and intelligently selects the best
/// account for each request based on:
/// - Subscription tier (ULTRA > PRO > FREE)
/// - Rate limit status
/// - Session stickiness requirements
/// - Token expiration
pub struct TokenManager {
    /// All loaded tokens, keyed by account_id
    tokens: Arc<DashMap<String, ProxyToken>>,
    /// Data directory for account files
    data_dir: PathBuf,
    /// Rate limit tracker
    rate_limit_tracker: Arc<RateLimitTracker>,
    /// Session manager for sticky bindings
    session_manager: SessionManager,
    /// Refresh coordinator for OAuth token refresh
    refresh_coordinator: RefreshCoordinator,
    /// Account scheduler
    scheduler: AccountScheduler,
    /// Scheduling configuration
    sticky_config: Arc<RwLock<StickySessionConfig>>,
}

impl TokenManager {
    /// Create a new TokenManager
    pub fn new(data_dir: PathBuf) -> Self {
        let rate_limit_tracker = Arc::new(RateLimitTracker::new());
        
        Self {
            tokens: Arc::new(DashMap::new()),
            data_dir,
            rate_limit_tracker: rate_limit_tracker.clone(),
            session_manager: SessionManager::new(),
            refresh_coordinator: RefreshCoordinator::new(),
            scheduler: AccountScheduler::new(rate_limit_tracker),
            // Use CacheFirst with 120s to match existing StickySessionConfig defaults
            sticky_config: Arc::new(RwLock::new(StickySessionConfig::default())),
        }
    }

    /// Load all accounts from the data directory
    /// 
    /// Returns the number of active accounts loaded.
    pub async fn load_accounts(&self) -> Result<usize, String> {
        let accounts_dir = self.data_dir.join("accounts");

        if !accounts_dir.exists() {
            return Err(format!("Accounts directory does not exist: {:?}", accounts_dir));
        }

        // Clear existing tokens (reload should reflect current disk state)
        self.tokens.clear();
        self.session_manager.clear_all();

        // Read directory entries in blocking task
        let accounts_dir_clone = accounts_dir.clone();
        let entries: Vec<PathBuf> = tokio::task::spawn_blocking(move || {
            std::fs::read_dir(&accounts_dir_clone)
                .map(|read_dir| {
                    read_dir
                        .filter_map(|e| e.ok())
                        .map(|e| e.path())
                        .filter(|p| p.extension().and_then(|s| s.to_str()) == Some("json"))
                        .collect::<Vec<_>>()
                })
        })
        .await
        .map_err(|e| format!("Task failed: {}", e))?
        .map_err(|e| format!("Failed to read accounts directory: {}", e))?;

        let mut count = 0;

        for path in entries {
            match self.load_single_account(&path).await {
                Ok(Some(token)) => {
                    self.tokens.insert(token.account_id.clone(), token);
                    count += 1;
                }
                Ok(None) => {
                    // Account is disabled, skip
                }
                Err(e) => {
                    tracing::debug!("Failed to load account {:?}: {}", path, e);
                }
            }
        }

        Ok(count)
    }

    /// Load a single account from a JSON file
    async fn load_single_account(&self, path: &PathBuf) -> Result<Option<ProxyToken>, String> {
        let path_clone = path.clone();
        let content = tokio::task::spawn_blocking(move || std::fs::read_to_string(&path_clone))
            .await
            .map_err(|e| format!("Task failed: {}", e))?
            .map_err(|e| format!("Failed to read file: {}", e))?;

        let account: serde_json::Value = serde_json::from_str(&content)
            .map_err(|e| format!("Failed to parse JSON: {}", e))?;

        // Check if account is disabled
        if account.get("disabled").and_then(|v| v.as_bool()).unwrap_or(false) {
            return Ok(None);
        }

        // Check if proxy is disabled for this account
        if account.get("proxy_disabled").and_then(|v| v.as_bool()).unwrap_or(false) {
            return Ok(None);
        }

        // Extract required fields
        let account_id = account["id"]
            .as_str()
            .ok_or("Missing id field")?
            .to_string();

        let email = account["email"]
            .as_str()
            .ok_or("Missing email field")?
            .to_string();

        let token_obj = account["token"]
            .as_object()
            .ok_or("Missing token field")?;

        let access_token = token_obj["access_token"]
            .as_str()
            .ok_or("Missing access_token")?
            .to_string();

        let refresh_token = token_obj["refresh_token"]
            .as_str()
            .ok_or("Missing refresh_token")?
            .to_string();

        let expires_in = token_obj["expires_in"]
            .as_i64()
            .ok_or("Missing expires_in")?;

        let timestamp = token_obj["expiry_timestamp"]
            .as_i64()
            .ok_or("Missing expiry_timestamp")?;

        let project_id = token_obj
            .get("project_id")
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());

        let subscription_tier = account
            .get("quota")
            .and_then(|q| q.get("subscription_tier"))
            .and_then(|v| v.as_str())
            .map(|s| s.to_string());

        Ok(Some(ProxyToken {
            account_id,
            access_token,
            refresh_token,
            expires_in,
            timestamp,
            email,
            account_path: path.clone(),
            project_id,
            subscription_tier,
        }))
    }

    /// Get a token for a request
    /// 
    /// # Arguments
    /// * `quota_group` - "claude" or "gemini"
    /// * `request_type` - "chat", "image_gen", etc.
    /// * `force_rotate` - Force account rotation
    /// * `session_id` - Optional session ID for sticky binding
    pub async fn get_token(
        &self,
        quota_group: &str,
        request_type: &str,
        force_rotate: bool,
        session_id: Option<&str>,
    ) -> Result<SelectedToken, String> {
        // Take snapshot of tokens
        let mut tokens_snapshot: Vec<ProxyToken> = self
            .tokens
            .iter()
            .map(|e| e.value().clone())
            .collect();

        if tokens_snapshot.is_empty() {
            return Err("Token pool is empty".to_string());
        }

        // Sort by subscription tier priority
        AccountScheduler::sort_by_tier(&mut tokens_snapshot);

        let scope_group = AccountScheduler::scope_group(quota_group, request_type);
        let scheduling = self.sticky_config.read().await.clone();

        // Get session binding if exists
        let bound_account = session_id
            .and_then(|sid| self.session_manager.get_binding(&scope_group, sid));

        tracing::info!(
            "[TokenManager] get_token: group={}, type={}, force_rotate={}, session={:?}",
            quota_group,
            request_type,
            force_rotate,
            session_id
        );

        let mut attempted = std::collections::HashSet::new();
        let mut last_error: Option<String> = None;

        // Try each account until one works
        for attempt in 0..tokens_snapshot.len() {
            let rotate = force_rotate || attempt > 0;

            // Get scheduling decision
            let decision = if rotate {
                // Force round-robin on rotation
                match self.scheduler.select_round_robin(&tokens_snapshot, &scope_group, &attempted) {
                    Some(token) => SchedulingDecision::UseAccount(token),
                    None => SchedulingDecision::AllUnavailable { min_wait_seconds: 60 },
                }
            } else {
                self.scheduler.select_with_session(
                    &tokens_snapshot,
                    &scope_group,
                    bound_account.as_deref(),
                    &scheduling,
                    &attempted,
                )
            };

            let mut token = match decision {
                SchedulingDecision::UseAccount(t) => t,
                SchedulingDecision::WaitAndUse { token, wait_seconds } => {
                    tracing::warn!(
                        "CacheFirst mode: waiting {}s for account {} to become available",
                        wait_seconds,
                        token.email
                    );
                    tokio::time::sleep(std::time::Duration::from_secs(wait_seconds)).await;
                    token
                }
                SchedulingDecision::AllUnavailable { min_wait_seconds } => {
                    return Err(format!(
                        "All accounts are currently limited. Please wait {}s.",
                        min_wait_seconds
                    ));
                }
            };

            // Check if token needs refresh
            if token.is_expired() {
                match self.refresh_token(&mut token).await {
                    Ok(()) => {
                        // Update token in storage
                        if let Some(mut entry) = self.tokens.get_mut(&token.account_id) {
                            entry.access_token = token.access_token.clone();
                            entry.expires_in = token.expires_in;
                            entry.timestamp = token.timestamp;
                        }
                    }
                    Err(e) => {
                        tracing::error!("Token refresh failed for {}: {}", token.email, e);
                        
                        if RefreshCoordinator::is_permanent_error(&e) {
                            tracing::error!("Disabling account due to permanent error: {}", token.email);
                            let _ = self.disable_account(&token.account_id, &e).await;
                            self.tokens.remove(&token.account_id);
                        }
                        
                        last_error = Some(format!("Token refresh failed: {}", e));
                        attempted.insert(token.account_id.clone());
                        continue;
                    }
                }
            }

            // Ensure we have a project_id
            let project_id = match &token.project_id {
                Some(pid) => pid.clone(),
                None => {
                    match self.fetch_and_save_project_id(&token).await {
                        Ok(pid) => pid,
                        Err(e) => {
                            last_error = Some(format!("Failed to fetch project_id: {}", e));
                            attempted.insert(token.account_id.clone());
                            continue;
                        }
                    }
                }
            };

            // Bind session to this account
            if let Some(sid) = session_id {
                if !rotate {
                    self.session_manager.set_binding(&scope_group, sid, &token.account_id);
                }
            }

            tracing::info!(
                "[TokenManager] Selected account: {} (id: {})",
                token.email,
                token.account_id
            );

            // Update current account in background
            let account_id = token.account_id.clone();
            tokio::spawn(async move {
                if let Err(e) = crate::modules::account::set_current_account_id(&account_id) {
                    tracing::debug!("Failed to update current_account_id: {}", e);
                }
            });

            return Ok(SelectedToken {
                access_token: token.access_token,
                project_id,
                email: token.email,
                account_id: token.account_id,
            });
        }

        Err(last_error.unwrap_or_else(|| "All accounts failed".to_string()))
    }

    /// Refresh a token using OAuth
    async fn refresh_token(&self, token: &mut ProxyToken) -> Result<(), String> {
        let lock = self.refresh_coordinator.get_lock(&token.account_id);
        let _guard = lock.lock().await;

        // Double-check if token still needs refresh
        if !token.is_expired() {
            // Another request already refreshed it
            if let Some(entry) = self.tokens.get(&token.account_id) {
                token.access_token = entry.access_token.clone();
                token.expires_in = entry.expires_in;
                token.timestamp = entry.timestamp;
            }
            return Ok(());
        }

        let response = crate::modules::oauth::refresh_access_token(&token.refresh_token)
            .await
            .map_err(|e| e.to_string())?;

        let now = chrono::Utc::now().timestamp();
        token.access_token = response.access_token.clone();
        token.expires_in = response.expires_in;
        token.timestamp = now + response.expires_in;

        // Save to disk
        RefreshCoordinator::save_refreshed_token(
            token,
            &TokenResponse {
                access_token: response.access_token,
                expires_in: response.expires_in,
            },
        )
        .await?;

        Ok(())
    }

    /// Fetch and save project ID for an account
    async fn fetch_and_save_project_id(&self, token: &ProxyToken) -> Result<String, String> {
        let project_id = crate::proxy::project_resolver::fetch_project_id(&token.access_token)
            .await
            .map_err(|e| format!("Failed to fetch project_id: {}", e))?;

        // Update in memory
        if let Some(mut entry) = self.tokens.get_mut(&token.account_id) {
            entry.project_id = Some(project_id.clone());
        }

        // Save to disk
        self.save_project_id(&token.account_id, &project_id).await?;

        Ok(project_id)
    }

    /// Save project_id to account file
    async fn save_project_id(&self, account_id: &str, project_id: &str) -> Result<(), String> {
        let entry = self.tokens.get(account_id).ok_or("Account not found")?;
        let path = entry.account_path.clone();
        drop(entry);

        let path_clone = path.clone();
        let content_str = tokio::task::spawn_blocking(move || std::fs::read_to_string(&path_clone))
            .await
            .map_err(|e| format!("Task failed: {}", e))?
            .map_err(|e| format!("Failed to read file: {}", e))?;

        let mut content: serde_json::Value = serde_json::from_str(&content_str)
            .map_err(|e| format!("Failed to parse JSON: {}", e))?;

        content["token"]["project_id"] = serde_json::Value::String(project_id.to_string());

        let json_str = serde_json::to_string_pretty(&content)
            .map_err(|e| format!("Failed to serialize JSON: {}", e))?;

        let path_clone = path.clone();
        tokio::task::spawn_blocking(move || std::fs::write(&path_clone, json_str))
            .await
            .map_err(|e| format!("Task failed: {}", e))?
            .map_err(|e| format!("Failed to write file: {}", e))?;

        Ok(())
    }

    /// Disable an account due to errors
    async fn disable_account(&self, account_id: &str, reason: &str) -> Result<(), String> {
        let path = if let Some(entry) = self.tokens.get(account_id) {
            entry.account_path.clone()
        } else {
            self.data_dir.join("accounts").join(format!("{}.json", account_id))
        };

        let path_clone = path.clone();
        let content_str = tokio::task::spawn_blocking(move || std::fs::read_to_string(&path_clone))
            .await
            .map_err(|e| format!("Task failed: {}", e))?
            .map_err(|e| format!("Failed to read file: {}", e))?;

        let mut content: serde_json::Value = serde_json::from_str(&content_str)
            .map_err(|e| format!("Failed to parse JSON: {}", e))?;

        let now = chrono::Utc::now().timestamp();
        content["disabled"] = serde_json::Value::Bool(true);
        content["disabled_at"] = serde_json::Value::Number(now.into());
        content["disabled_reason"] = serde_json::Value::String(truncate_string(reason, 800));

        let json_str = serde_json::to_string_pretty(&content)
            .map_err(|e| format!("Failed to serialize JSON: {}", e))?;

        let path_clone = path.clone();
        tokio::task::spawn_blocking(move || std::fs::write(&path_clone, json_str))
            .await
            .map_err(|e| format!("Task failed: {}", e))?
            .map_err(|e| format!("Failed to write file: {}", e))?;

        tracing::warn!("Account disabled: {} ({:?})", account_id, path);
        Ok(())
    }

    /// Get the number of loaded accounts
    pub fn len(&self) -> usize {
        self.tokens.len()
    }

    /// Check if no accounts are loaded
    pub fn is_empty(&self) -> bool {
        self.tokens.is_empty()
    }

    // ===== Rate Limit Management =====

    /// Mark an account as rate limited
    pub fn mark_rate_limited(
        &self,
        quota_group: &str,
        request_type: &str,
        account_id: &str,
        status: u16,
        retry_after_header: Option<&str>,
        error_body: &str,
    ) {
        let scope_group = AccountScheduler::scope_group(quota_group, request_type);
        self.rate_limit_tracker.parse_from_error(
            &scope_group,
            account_id,
            status,
            retry_after_header,
            error_body,
        );
    }

    /// Check if an account is rate limited
    pub fn is_rate_limited(&self, quota_group: &str, request_type: &str, account_id: &str) -> bool {
        let scope_group = AccountScheduler::scope_group(quota_group, request_type);
        self.rate_limit_tracker.is_rate_limited(&scope_group, account_id)
    }

    // ===== Scheduling Configuration =====

    /// Get current scheduling configuration
    pub async fn get_sticky_config(&self) -> StickySessionConfig {
        self.sticky_config.read().await.clone()
    }

    /// Update scheduling configuration
    pub async fn update_sticky_config(&self, new_config: StickySessionConfig) {
        let mut config = self.sticky_config.write().await;
        *config = new_config;
        tracing::debug!("Scheduling configuration updated: {:?}", *config);
    }

    /// Clear all session bindings
    pub fn clear_all_sessions(&self) {
        self.session_manager.clear_all();
    }
}

/// Truncate a string to a maximum length
fn truncate_string(s: &str, max_len: usize) -> String {
    if s.chars().count() <= max_len {
        return s.to_string();
    }
    let mut result: String = s.chars().take(max_len).collect();
    result.push('…');
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_truncate_string() {
        assert_eq!(truncate_string("hello", 10), "hello");
        assert_eq!(truncate_string("hello world", 5), "hello…");
        assert_eq!(truncate_string("", 5), "");
    }

    #[tokio::test]
    async fn test_token_manager_creation() {
        let tm = TokenManager::new(PathBuf::from("/tmp"));
        assert!(tm.is_empty());
        assert_eq!(tm.len(), 0);
    }

    #[tokio::test]
    async fn test_sticky_config_update() {
        let tm = TokenManager::new(PathBuf::from("/tmp"));
        
        let initial = tm.get_sticky_config().await;
        // Default is CacheFirst with 120 seconds from StickySessionConfig
        assert_eq!(initial.max_wait_seconds, 120);
        
        let new_config = StickySessionConfig {
            mode: crate::proxy::sticky_config::SchedulingMode::Balance,
            max_wait_seconds: 60,
        };
        
        tm.update_sticky_config(new_config.clone()).await;
        
        let updated = tm.get_sticky_config().await;
        assert_eq!(updated.max_wait_seconds, 60);
    }

    #[tokio::test]
    async fn test_session_clearing() {
        let tm = TokenManager::new(PathBuf::from("/tmp"));
        
        // This would normally be set during get_token
        tm.session_manager.set_binding("claude", "session-1", "account-1");
        assert_eq!(tm.session_manager.len(), 1);
        
        tm.clear_all_sessions();
        assert!(tm.session_manager.is_empty());
    }
}
