-- Raven Database Initialization Script
-- Target: PostgreSQL

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    username_lower TEXT NOT NULL UNIQUE,
    password_hash TEXT,
    email TEXT,
    display_name TEXT,
    avatar_url TEXT,
    auth_source TEXT NOT NULL DEFAULT 'local',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. OAuth Accounts
CREATE TABLE IF NOT EXISTS oauth_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_user_id TEXT NOT NULL,
    email TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, provider_user_id),
    UNIQUE (user_id, provider)
);

-- 3. RSS Subscriptions (Discord)
CREATE TABLE IF NOT EXISTS rss_subscriptions (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT,
    channel_id BIGINT NOT NULL,
    provider TEXT NOT NULL,
    category TEXT NOT NULL,
    topic TEXT NOT NULL,
    UNIQUE (guild_id, channel_id, provider, category, topic)
);

-- 4. User Feed Preferences (Cloud Sync)
CREATE TABLE IF NOT EXISTS user_feed_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    category TEXT NOT NULL,
    topic TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, provider, category, topic)
);

-- 5. User Custom Feeds
CREATE TABLE IF NOT EXISTS user_custom_feeds (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'custom',
    topic TEXT NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, url)
);

-- 6. OAuth Link Requests (Temporary State)
CREATE TABLE IF NOT EXISTS user_oauth_link_requests (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    state_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7. User Saved Articles (Archive)
CREATE TABLE IF NOT EXISTS user_saved_articles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    summary TEXT,
    source TEXT,
    saved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, url)
);

-- Indices for common lookups
CREATE INDEX IF NOT EXISTS idx_users_username_lower ON users(username_lower);
CREATE INDEX IF NOT EXISTS idx_rss_subscriptions_channel ON rss_subscriptions(channel_id);
CREATE INDEX IF NOT EXISTS idx_user_feed_prefs_user ON user_feed_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_saved_articles_user ON user_saved_articles(user_id);
