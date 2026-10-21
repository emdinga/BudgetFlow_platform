CREATE TABLE IF NOT EXISTS transactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    direction TEXT NOT NULL CHECK (direction IN ('income', 'expense')),
    amount NUMERIC(12, 2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    category TEXT NOT NULL CHECK (char_length(category) BETWEEN 1 AND 50),
    description TEXT NOT NULL CHECK (char_length(description) BETWEEN 1 AND 200),
    occurred_on DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS transactions_occurred_on_id_idx
    ON transactions (occurred_on DESC, id DESC);
