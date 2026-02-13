-- Add soft delete columns to stripe_accounts table
-- Migration: Add deleted_at and deleted_by for soft delete functionality

-- Add deleted_at column
ALTER TABLE stripe_accounts
ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP WITH TIME ZONE;

-- Add deleted_by column (references users)
ALTER TABLE stripe_accounts
ADD COLUMN IF NOT EXISTS deleted_by UUID REFERENCES users(id);

-- Create index on deleted_at for faster queries
CREATE INDEX IF NOT EXISTS idx_stripe_accounts_deleted_at ON stripe_accounts(deleted_at);

-- Add foreign key constraint if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'stripe_accounts_deleted_by_fkey'
    ) THEN
        ALTER TABLE stripe_accounts
        ADD CONSTRAINT stripe_accounts_deleted_by_fkey
        FOREIGN KEY (deleted_by) REFERENCES users(id);
    END IF;
END $$;
