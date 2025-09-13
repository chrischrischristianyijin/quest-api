-- 为用户profile表添加记忆档案字段
-- 支持自动储存和整合用户记忆

-- 添加memory_profile字段到profiles表
ALTER TABLE profiles 
ADD COLUMN IF NOT EXISTS memory_profile JSONB DEFAULT '{}';

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_profiles_memory_profile 
ON profiles USING gin(memory_profile);

-- 添加注释说明
COMMENT ON COLUMN profiles.memory_profile IS '用户记忆档案，包含整合后的用户偏好、事实、上下文和洞察信息';

-- 创建函数来更新memory_profile
CREATE OR REPLACE FUNCTION update_user_memory_profile(
    p_user_id UUID,
    p_memory_profile JSONB
) RETURNS BOOLEAN AS $$
BEGIN
    UPDATE profiles 
    SET 
        memory_profile = p_memory_profile,
        updated_at = NOW()
    WHERE id = p_user_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- 创建函数来获取用户的记忆档案摘要
CREATE OR REPLACE FUNCTION get_user_memory_summary(p_user_id UUID)
RETURNS JSONB AS $$
DECLARE
    memory_profile JSONB;
    summary JSONB;
BEGIN
    -- 获取用户的记忆档案
    SELECT memory_profile INTO memory_profile
    FROM profiles 
    WHERE id = p_user_id;
    
    -- 如果memory_profile为空，返回默认值
    IF memory_profile IS NULL OR memory_profile = '{}' THEN
        summary := jsonb_build_object(
            'total_memories', 0,
            'by_type', jsonb_build_object(
                'preferences', 0,
                'facts', 0,
                'context', 0,
                'insights', 0
            ),
            'last_consolidated', null,
            'consolidation_settings', jsonb_build_object(
                'auto_consolidate', true,
                'consolidation_threshold', 0.8,
                'max_memories_per_type', 50
            )
        );
    ELSE
        -- 计算记忆摘要
        summary := jsonb_build_object(
            'total_memories', 
            COALESCE(jsonb_array_length(memory_profile->'preferences'), 0) +
            COALESCE(jsonb_array_length(memory_profile->'facts'), 0) +
            COALESCE(jsonb_array_length(memory_profile->'context'), 0) +
            COALESCE(jsonb_array_length(memory_profile->'insights'), 0),
            'by_type', jsonb_build_object(
                'preferences', COALESCE(jsonb_array_length(memory_profile->'preferences'), 0),
                'facts', COALESCE(jsonb_array_length(memory_profile->'facts'), 0),
                'context', COALESCE(jsonb_array_length(memory_profile->'context'), 0),
                'insights', COALESCE(jsonb_array_length(memory_profile->'insights'), 0)
            ),
            'last_consolidated', memory_profile->'last_consolidated',
            'consolidation_settings', COALESCE(memory_profile->'consolidation_settings', '{}')
        );
    END IF;
    
    RETURN summary;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器，当memory_profile更新时自动更新updated_at
CREATE OR REPLACE FUNCTION update_memory_profile_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    -- 只有当memory_profile字段发生变化时才更新updated_at
    IF OLD.memory_profile IS DISTINCT FROM NEW.memory_profile THEN
        NEW.updated_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_memory_profile_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_memory_profile_updated_at();

-- 创建视图来方便查询用户的记忆档案
CREATE OR REPLACE VIEW user_memory_profiles AS
SELECT 
    p.id as user_id,
    p.nickname,
    p.memory_profile,
    get_user_memory_summary(p.id) as memory_summary,
    p.updated_at as last_profile_update
FROM profiles p
WHERE p.memory_profile IS NOT NULL 
AND p.memory_profile != '{}';

-- 添加视图注释
COMMENT ON VIEW user_memory_profiles IS '用户记忆档案视图，提供记忆摘要和统计信息';

-- 创建示例数据（可选）
-- 为测试用户添加示例记忆档案
-- INSERT INTO profiles (id, nickname, memory_profile) 
-- VALUES (
--     '00000000-0000-0000-0000-000000000001',
--     '测试用户',
--     '{
--         "preferences": {
--             "memory_1": {
--                 "content": "用户喜欢在早上工作",
--                 "importance": 0.8,
--                 "created_at": "2024-01-15T10:30:00Z",
--                 "metadata": {"source": "conversation"}
--             }
--         },
--         "facts": {},
--         "context": {},
--         "insights": {},
--         "last_consolidated": "2024-01-15T10:30:00Z",
--         "consolidation_settings": {
--             "auto_consolidate": true,
--             "consolidation_threshold": 0.8,
--             "max_memories_per_type": 50
--         }
--     }'
-- ) ON CONFLICT (id) DO NOTHING;
