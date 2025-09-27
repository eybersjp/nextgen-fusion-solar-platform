-- Migration: 004_create_currency_tables.sql
-- Phase 3: Create currency tables for multi-currency support

-- Create exchange_rates table
CREATE TABLE exchange_rates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_currency CHAR(3) NOT NULL,
    to_currency CHAR(3) NOT NULL,
    rate DECIMAL(15,8) NOT NULL CHECK (rate > 0),
    effective_date DATE NOT NULL,
    source VARCHAR(50) NOT NULL DEFAULT 'manual',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(from_currency, to_currency, effective_date)
);

CREATE TRIGGER update_exchange_rates_updated_at
    BEFORE UPDATE ON exchange_rates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create multi_currency_transactions table
CREATE TABLE multi_currency_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    transaction_type VARCHAR(50) NOT NULL CHECK (transaction_type IN ('invoice', 'payment', 'expense', 'quote', 'contract')),
    reference_id UUID, -- References to invoices, payments, etc.
    original_amount DECIMAL(15,2) NOT NULL,
    original_currency CHAR(3) NOT NULL,
    converted_amount DECIMAL(15,2),
    converted_currency CHAR(3),
    exchange_rate DECIMAL(15,8),
    conversion_date TIMESTAMP WITH TIME ZONE,
    description TEXT,
    transaction_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TRIGGER update_multi_currency_transactions_updated_at
    BEFORE UPDATE ON multi_currency_transactions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create currency_preferences table
CREATE TABLE currency_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(50) NOT NULL CHECK (entity_type IN ('organization', 'user', 'project', 'customer')),
    entity_id UUID NOT NULL,
    preferred_currency CHAR(3) NOT NULL,
    display_format VARCHAR(50) DEFAULT 'symbol_amount', -- symbol_amount, amount_symbol, code_amount
    decimal_places INTEGER DEFAULT 2 CHECK (decimal_places >= 0 AND decimal_places <= 8),
    thousands_separator VARCHAR(1) DEFAULT ',',
    decimal_separator VARCHAR(1) DEFAULT '.',
    auto_convert BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(entity_type, entity_id)
);

CREATE TRIGGER update_currency_preferences_updated_at
    BEFORE UPDATE ON currency_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create supported_currencies table
CREATE TABLE supported_currencies (
    code CHAR(3) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    symbol VARCHAR(10),
    decimal_places INTEGER DEFAULT 2,
    is_active BOOLEAN DEFAULT true,
    country_code CHAR(2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TRIGGER update_supported_currencies_updated_at
    BEFORE UPDATE ON supported_currencies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default supported currencies (ZAR, AUD, USD as per user rules)
INSERT INTO supported_currencies (code, name, symbol, decimal_places, country_code) VALUES
('ZAR', 'South African Rand', 'R', 2, 'ZA'),
('AUD', 'Australian Dollar', 'A$', 2, 'AU'),
('USD', 'United States Dollar', '$', 2, 'US'),
('EUR', 'Euro', '€', 2, 'EU'),
('GBP', 'British Pound Sterling', '£', 2, 'GB'),
('CAD', 'Canadian Dollar', 'C$', 2, 'CA'),
('JPY', 'Japanese Yen', '¥', 0, 'JP'),
('CHF', 'Swiss Franc', 'CHF', 2, 'CH'),
('CNY', 'Chinese Yuan', '¥', 2, 'CN'),
('INR', 'Indian Rupee', '₹', 2, 'IN');

-- Create currency_conversion_logs table for audit trail
CREATE TABLE currency_conversion_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    transaction_id UUID REFERENCES multi_currency_transactions(id) ON DELETE CASCADE,
    from_currency CHAR(3) NOT NULL,
    to_currency CHAR(3) NOT NULL,
    original_amount DECIMAL(15,2) NOT NULL,
    converted_amount DECIMAL(15,2) NOT NULL,
    exchange_rate DECIMAL(15,8) NOT NULL,
    conversion_method VARCHAR(50) DEFAULT 'api', -- api, manual, cached
    conversion_source VARCHAR(100),
    converted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    converted_by UUID REFERENCES users(id)
);

-- Create indexes for performance
CREATE INDEX idx_exchange_rates_currencies ON exchange_rates(from_currency, to_currency);
CREATE INDEX idx_exchange_rates_effective_date ON exchange_rates(effective_date DESC);
CREATE INDEX idx_exchange_rates_source ON exchange_rates(source);

CREATE INDEX idx_multi_currency_transactions_project_id ON multi_currency_transactions(project_id);
CREATE INDEX idx_multi_currency_transactions_type ON multi_currency_transactions(transaction_type);
CREATE INDEX idx_multi_currency_transactions_date ON multi_currency_transactions(transaction_date DESC);
CREATE INDEX idx_multi_currency_transactions_currency ON multi_currency_transactions(original_currency);

CREATE INDEX idx_currency_preferences_entity ON currency_preferences(entity_type, entity_id);
CREATE INDEX idx_currency_preferences_currency ON currency_preferences(preferred_currency);

CREATE INDEX idx_supported_currencies_active ON supported_currencies(is_active);
CREATE INDEX idx_supported_currencies_country ON supported_currencies(country_code);

CREATE INDEX idx_currency_conversion_logs_transaction_id ON currency_conversion_logs(transaction_id);
CREATE INDEX idx_currency_conversion_logs_converted_at ON currency_conversion_logs(converted_at DESC);
CREATE INDEX idx_currency_conversion_logs_currencies ON currency_conversion_logs(from_currency, to_currency);