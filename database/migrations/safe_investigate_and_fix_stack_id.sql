-- SAFE INVESTIGATION AND FIX FOR STACK_ID TYPE MISMATCH
-- This migration is designed to be safe and reversible

-- ========================================
-- STEP 1: INVESTIGATE CURRENT STATE
-- ========================================

-- Check the current data types and constraints
SELECT 
    'INVESTIGATION: Current table structure' as step,
    'stacks' as table_name,
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'stacks' AND column_name = 'id'
UNION ALL
SELECT 
    'INVESTIGATION: Current table structure' as step,
    'insights' as table_name,
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'insights' AND column_name = 'stack_id';

-- Check if there are any existing foreign key constraints
SELECT 
    'INVESTIGATION: Foreign key constraints' as step,
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND (tc.table_name = 'insights' OR tc.table_name = 'stacks')
    AND (kcu.column_name = 'stack_id' OR kcu.column_name = 'id');

-- Check if there are any existing stack_id values in insights table
SELECT 
    'INVESTIGATION: Existing stack_id values' as step,
    COUNT(*) as total_insights,
    COUNT(stack_id) as insights_with_stack_id,
    COUNT(CASE WHEN stack_id IS NOT NULL THEN 1 END) as non_null_stack_ids
FROM insights;

-- Check if there are any existing stacks
SELECT 
    'INVESTIGATION: Existing stacks' as step,
    COUNT(*) as total_stacks,
    COUNT(id) as stacks_with_id
FROM stacks;

-- ========================================
-- STEP 2: SAFE BACKUP AND PREPARATION
-- ========================================

-- Create a backup table of current insights with stack_id
CREATE TABLE IF NOT EXISTS insights_backup_stack_id AS 
SELECT id, stack_id, created_at, updated_at 
FROM insights 
WHERE stack_id IS NOT NULL;

-- Log the backup
SELECT 
    'BACKUP: Created backup table' as step,
    COUNT(*) as backed_up_insights
FROM insights_backup_stack_id;

-- ========================================
-- STEP 3: SAFE MIGRATION (ONLY IF NO DATA LOSS)
-- ========================================

-- Only proceed if there are no existing stack relationships (due to type mismatch)
-- This ensures we don't lose any data
DO $$
DECLARE
    existing_stack_relationships INTEGER;
BEGIN
    -- Count insights that have stack_id values
    SELECT COUNT(*) INTO existing_stack_relationships 
    FROM insights 
    WHERE stack_id IS NOT NULL;
    
    -- Only proceed if there are no existing relationships
    -- (This is expected due to the type mismatch)
    IF existing_stack_relationships = 0 THEN
        RAISE NOTICE 'SAFE TO PROCEED: No existing stack relationships found. Type mismatch prevents data loss.';
        
        -- Step 3a: Drop existing foreign key constraint (if it exists)
        ALTER TABLE insights DROP CONSTRAINT IF EXISTS insights_stack_id_fkey;
        
        -- Step 3b: Change column type from INTEGER to UUID
        ALTER TABLE insights ALTER COLUMN stack_id TYPE UUID USING NULL;
        
        -- Step 3c: Add proper foreign key constraint
        ALTER TABLE insights ADD CONSTRAINT insights_stack_id_fkey 
            FOREIGN KEY (stack_id) REFERENCES stacks(id) ON DELETE SET NULL;
        
        -- Step 3d: Recreate index
        DROP INDEX IF EXISTS idx_insights_stack_id;
        CREATE INDEX idx_insights_stack_id ON insights(stack_id);
        
        RAISE NOTICE 'MIGRATION COMPLETED: stack_id column successfully changed to UUID type.';
        
    ELSE
        RAISE WARNING 'MIGRATION ABORTED: Found % existing stack relationships. Manual review required.', existing_stack_relationships;
        RAISE WARNING 'Please review the data in insights_backup_stack_id table before proceeding.';
    END IF;
END $$;

-- ========================================
-- STEP 4: VERIFICATION
-- ========================================

-- Verify the final state
SELECT 
    'VERIFICATION: Final table structure' as step,
    'stacks' as table_name,
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'stacks' AND column_name = 'id'
UNION ALL
SELECT 
    'VERIFICATION: Final table structure' as step,
    'insights' as table_name,
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns 
WHERE table_name = 'insights' AND column_name = 'stack_id';

-- Verify foreign key constraint exists
SELECT 
    'VERIFICATION: Foreign key constraint' as step,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE constraint_name = 'insights_stack_id_fkey' 
            AND table_name = 'insights'
        ) THEN 'PASS - Foreign key exists'
        ELSE 'FAIL - Foreign key missing'
    END as result;

-- ========================================
-- STEP 5: CLEANUP (OPTIONAL)
-- ========================================

-- Uncomment the line below to remove the backup table after verification
-- DROP TABLE IF EXISTS insights_backup_stack_id;

