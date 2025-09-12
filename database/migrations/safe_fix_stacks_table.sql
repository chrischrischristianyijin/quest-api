-- Safe fix for stacks table - no destructive operations
-- This script only adds missing columns and creates triggers safely

-- First, let's see what columns currently exist
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'stacks' 
ORDER BY ordinal_position;

-- Add missing columns if they don't exist (safe operation)
ALTER TABLE stacks ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE stacks ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE stacks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Create the updated_at trigger function (safe operation)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Only create trigger if it doesn't exist (safe operation)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_stacks_updated_at') THEN
        CREATE TRIGGER update_stacks_updated_at 
            BEFORE UPDATE ON stacks 
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Verify the final table structure
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'stacks' 
ORDER BY ordinal_position;
