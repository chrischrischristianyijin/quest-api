-- Ensure stacks table exists with correct structure
CREATE TABLE IF NOT EXISTS stacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Ensure insights table has stack_id column (matching stacks.id type: int4)
ALTER TABLE insights ADD COLUMN IF NOT EXISTS stack_id INTEGER REFERENCES stacks(id) ON DELETE SET NULL;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_stacks_user_id ON stacks(user_id);
CREATE INDEX IF NOT EXISTS idx_stacks_created_at ON stacks(created_at);
CREATE INDEX IF NOT EXISTS idx_insights_stack_id ON insights(stack_id);

-- Create updated_at trigger for stacks table
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

-- Add RLS (Row Level Security) policies
ALTER TABLE stacks ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own stacks
CREATE POLICY "Users can view their own stacks" ON stacks
    FOR SELECT USING (auth.uid() = user_id);

-- Policy: Users can insert their own stacks
CREATE POLICY "Users can insert their own stacks" ON stacks
    FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own stacks
CREATE POLICY "Users can update their own stacks" ON stacks
    FOR UPDATE USING (auth.uid() = user_id);

-- Policy: Users can delete their own stacks
CREATE POLICY "Users can delete their own stacks" ON stacks
    FOR DELETE USING (auth.uid() = user_id);
