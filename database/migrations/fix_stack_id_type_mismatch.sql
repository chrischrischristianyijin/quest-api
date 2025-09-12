-- Fix stack_id type mismatch between stacks and insights tables
-- This migration changes insights.stack_id from INTEGER to UUID to match stacks.id

-- First, let's check the current state of both tables
SELECT 
    'stacks' as table_name,
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'stacks' AND column_name = 'id'
UNION ALL
SELECT 
    'insights' as table_name,
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'insights' AND column_name = 'stack_id';

-- Step 1: Drop the existing foreign key constraint
ALTER TABLE insights DROP CONSTRAINT IF EXISTS insights_stack_id_fkey;

-- Step 2: Change the stack_id column type from INTEGER to UUID
-- First, we need to handle any existing data
-- Since we're changing from INTEGER to UUID, we need to clear existing data
-- (This is safe because the type mismatch means no valid relationships exist)
UPDATE insights SET stack_id = NULL WHERE stack_id IS NOT NULL;

-- Now change the column type
ALTER TABLE insights ALTER COLUMN stack_id TYPE UUID USING NULL;

-- Step 3: Recreate the foreign key constraint with the correct types
ALTER TABLE insights ADD CONSTRAINT insights_stack_id_fkey 
    FOREIGN KEY (stack_id) REFERENCES stacks(id) ON DELETE SET NULL;

-- Step 4: Recreate the index for better performance
DROP INDEX IF EXISTS idx_insights_stack_id;
CREATE INDEX idx_insights_stack_id ON insights(stack_id);

-- Verify the fix
SELECT 
    'stacks' as table_name,
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'stacks' AND column_name = 'id'
UNION ALL
SELECT 
    'insights' as table_name,
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'insights' AND column_name = 'stack_id';

-- Test the foreign key constraint
SELECT 
    'Foreign key constraint test' as test_name,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'insights_stack_id_fkey' 
            AND table_name = 'insights'
        ) THEN 'PASS - Foreign key exists'
        ELSE 'FAIL - Foreign key missing'
    END as result;

