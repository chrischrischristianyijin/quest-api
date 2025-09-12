-- Fix stacks table to match the expected schema
-- This script will add missing columns and ensure the table structure is correct

-- First, let's see what columns currently exist
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'stacks' 
ORDER BY ordinal_position;

-- Add missing columns if they don't exist
ALTER TABLE stacks ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE stacks ADD COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();
ALTER TABLE stacks ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- Create or replace the updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop existing trigger if it exists and recreate it
DROP TRIGGER IF EXISTS update_stacks_updated_at ON stacks;
CREATE TRIGGER update_stacks_updated_at 
    BEFORE UPDATE ON stacks 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Verify the final table structure
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name = 'stacks' 
ORDER BY ordinal_position;
