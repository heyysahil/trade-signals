-- PostgreSQL schema for Send Signals (fresh setup).
-- Run this on an empty database, or use app startup (db.create_all()) to create tables.
-- cPanel: create database and user first, then run this or let the app create tables.

-- Users (customers)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    mobile VARCHAR(15) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT TRUE
);

-- Admins (staff / superadmin)
CREATE TABLE IF NOT EXISTS admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'staff',
    product_category VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

-- Products (subscription products)
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price NUMERIC(10, 2) NOT NULL,
    duration_days INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

-- Subscriptions (user product subscriptions)
CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    start_date TIMESTAMP WITH TIME ZONE NOT NULL,
    end_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    payment_status VARCHAR(20) DEFAULT 'pending',
    approved_by INTEGER REFERENCES admins(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    rejection_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

-- Transactions (payments)
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    subscription_id INTEGER REFERENCES subscriptions(id),
    amount NUMERIC(10, 2) NOT NULL,
    payment_method VARCHAR(50),
    payment_reference VARCHAR(100) UNIQUE,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

-- Signals (trading signals)
CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id),
    symbol VARCHAR(50) NOT NULL,
    exchange VARCHAR(50),
    signal_type VARCHAR(10) NOT NULL,
    entry_price NUMERIC(10, 2) NOT NULL,
    entry_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    exit_price NUMERIC(10, 2),
    exit_time TIMESTAMP WITH TIME ZONE,
    target_price NUMERIC(10, 2),
    stop_loss NUMERIC(10, 2),
    live_price NUMERIC(10, 2),
    status VARCHAR(20) DEFAULT 'PENDING',
    approval_status VARCHAR(20) DEFAULT 'PENDING',
    approved_by INTEGER REFERENCES admins(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    profit_loss NUMERIC(10, 2) DEFAULT 0,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

-- Settings (key-value app config)
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

-- Email verification OTP
CREATE TABLE IF NOT EXISTS email_verification_otp (
    email VARCHAR(120) PRIMARY KEY,
    otp_hash VARCHAR(255) NOT NULL,
    otp_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    otp_attempts INTEGER DEFAULT 0,
    email_verified INTEGER DEFAULT 0,
    otp_sent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);

-- CAPTCHA challenges
CREATE TABLE IF NOT EXISTS captcha_challenge (
    captcha_id VARCHAR(64) PRIMARY KEY,
    captcha_answer VARCHAR(32) NOT NULL,
    captcha_expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used INTEGER DEFAULT 0
);

-- OTP send log (rate limiting)
CREATE TABLE IF NOT EXISTS otp_send_log (
    id SERIAL PRIMARY KEY,
    email VARCHAR(120) NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);
CREATE INDEX IF NOT EXISTS ix_otp_send_log_email ON otp_send_log(email);
CREATE INDEX IF NOT EXISTS ix_otp_send_log_sent_at ON otp_send_log(sent_at);

-- Admin notifications
CREATE TABLE IF NOT EXISTS admin_notifications (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    related_id INTEGER,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
);
