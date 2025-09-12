-- Add missing description column to existing stacks table
-- This script is safe to run multiple times

-- Add the description column if it doesn't exist
ALTER TABLE stacks ADD COLUMN IF NOT EXISTS description TEXT;

-- Update the updated_at trigger if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Only create trigger if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_stacks_updated_at') THEN
        CREATE TRIGGER update_stacks_updated_at 
            BEFORE UPDATE ON stacks 
            FOR EACH ROW 
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- Verify the column was added
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'stacks' 
AND column_name = 'description';
