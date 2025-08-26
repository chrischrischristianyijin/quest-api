-- Quest API 数据库触发器
-- 用于自动同步用户认证和资料数据

-- 创建自动同步触发器函数
CREATE OR REPLACE FUNCTION public.create_profile_for_new_user()
RETURNS TRIGGER AS $$
DECLARE
    username_candidate TEXT;
    base_username TEXT;
    unique_suffix TEXT;
BEGIN
    -- 生成唯一用户名
    base_username := LOWER(REGEXP_REPLACE(NEW.email, '@.*', ''));
    -- 清理用户名，只保留字母数字和下划线
    base_username := REGEXP_REPLACE(base_username, '[^a-zA-Z0-9_]', '', 'g');
    -- 确保用户名不为空
    IF base_username = '' THEN
        base_username := 'user';
    END IF;
    
    -- 生成唯一后缀（使用邮箱的哈希值）
    unique_suffix := SUBSTRING(MD5(NEW.email), 1, 8);
    username_candidate := base_username || '_' || unique_suffix;
    
    -- 尝试插入 profile
    INSERT INTO public.profiles (
        id, 
        username, 
        email,
        nickname,
        created_at,
        updated_at
    ) VALUES (
        NEW.id, 
        username_candidate,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'nickname', username_candidate),
        NOW(),
        NOW()
    ) ON CONFLICT (id) DO NOTHING;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 创建触发器
DROP TRIGGER IF EXISTS create_profile_for_new_user ON auth.users;
CREATE TRIGGER create_profile_for_new_user
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION public.create_profile_for_new_user();

-- 创建用户标签触发器函数
CREATE OR REPLACE FUNCTION public.create_default_tags_for_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- 为新用户添加默认标签
    INSERT INTO public.user_tags (user_id, name, color, created_at, updated_at)
    VALUES 
        (NEW.id, 'Technology', '#3B82F6', NOW(), NOW()),
        (NEW.id, 'Programming', '#10B981', NOW(), NOW()),
        (NEW.id, 'AI', '#8B5CF6', NOW(), NOW()),
        (NEW.id, 'Web Development', '#EF4444', NOW(), NOW()),
        (NEW.id, 'Learning', '#84CC16', NOW(), NOW()),
        (NEW.id, 'Tutorial', '#F97316', NOW(), NOW()),
        (NEW.id, 'Article', '#059669', NOW(), NOW()),
        (NEW.id, 'Video', '#DC2626', NOW(), NOW()),
        (NEW.id, 'Business', '#1F2937', NOW(), NOW()),
        (NEW.id, 'Productivity', '#047857', NOW(), NOW()),
        (NEW.id, 'Design', '#BE185D', NOW(), NOW()),
        (NEW.id, 'Tool', '#7C2D12', NOW(), NOW()),
        (NEW.id, 'Resource', '#1E40AF', NOW(), NOW()),
        (NEW.id, 'Project', '#7C3AED', NOW(), NOW()),
        (NEW.id, 'Ideas', '#F59E0B', NOW(), NOW())
    ON CONFLICT (user_id, name) DO NOTHING;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 创建用户标签触发器
DROP TRIGGER IF EXISTS create_default_tags_for_new_user ON public.profiles;
CREATE TRIGGER create_default_tags_for_new_user
AFTER INSERT ON public.profiles
FOR EACH ROW
EXECUTE FUNCTION public.create_default_tags_for_new_user();

-- 创建用户资料更新触发器函数
CREATE OR REPLACE FUNCTION public.update_profile_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 创建用户资料更新时间戳触发器
DROP TRIGGER IF EXISTS update_profile_timestamp ON public.profiles;
CREATE TRIGGER update_profile_timestamp
BEFORE UPDATE ON public.profiles
FOR EACH ROW
EXECUTE FUNCTION public.update_profile_timestamp();

-- 创建用户标签更新时间戳触发器
DROP TRIGGER IF EXISTS update_user_tag_timestamp ON public.user_tags;
CREATE TRIGGER update_user_tag_timestamp
BEFORE UPDATE ON public.user_tags
FOR EACH ROW
EXECUTE FUNCTION public.update_profile_timestamp();

-- 创建见解更新时间戳触发器
DROP TRIGGER IF EXISTS update_insight_timestamp ON public.insights;
CREATE TRIGGER update_insight_timestamp
BEFORE UPDATE ON public.insights
FOR EACH ROW
EXECUTE FUNCTION public.update_profile_timestamp();

-- 创建软删除触发器函数
CREATE OR REPLACE FUNCTION public.soft_delete_insight()
RETURNS TRIGGER AS $$
BEGIN
    -- 如果设置了软删除，则更新deleted_at字段而不是真正删除
    IF OLD.deleted_at IS NULL THEN
        NEW.deleted_at = NOW();
        RETURN NEW;
    ELSE
        RETURN OLD;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 创建见解软删除触发器
DROP TRIGGER IF EXISTS soft_delete_insight ON public.insights;
CREATE TRIGGER soft_delete_insight
BEFORE DELETE ON public.insights
FOR EACH ROW
EXECUTE FUNCTION public.soft_delete_insight();

-- 创建用户标签软删除触发器
DROP TRIGGER IF EXISTS soft_delete_user_tag ON public.user_tags;
CREATE TRIGGER soft_delete_user_tag
BEFORE DELETE ON public.user_tags
FOR EACH ROW
EXECUTE FUNCTION public.soft_delete_insight();

-- 创建用户资料软删除触发器
DROP TRIGGER IF EXISTS soft_delete_profile ON public.profiles;
CREATE TRIGGER soft_delete_profile
BEFORE DELETE ON public.profiles
FOR EACH ROW
EXECUTE FUNCTION public.soft_delete_insight();

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_username ON public.profiles(username);
CREATE INDEX IF NOT EXISTS idx_user_tags_user_id ON public.user_tags(user_id);
CREATE INDEX IF NOT EXISTS idx_insights_user_id ON public.insights(user_id);
CREATE INDEX IF NOT EXISTS idx_insights_deleted_at ON public.insights(deleted_at);

-- 创建全文搜索索引
CREATE INDEX IF NOT EXISTS idx_insights_content_search ON public.insights USING gin(to_tsvector('english', title || ' ' || content));
CREATE INDEX IF NOT EXISTS idx_profiles_search ON public.profiles USING gin(to_tsvector('english', nickname || ' ' || COALESCE(bio, '')));

-- 创建唯一约束
ALTER TABLE public.profiles ADD CONSTRAINT unique_profiles_email UNIQUE (email);
ALTER TABLE public.profiles ADD CONSTRAINT unique_profiles_username UNIQUE (username);
ALTER TABLE public.user_tags ADD CONSTRAINT unique_user_tags_name_per_user UNIQUE (user_id, name);

-- 添加注释
COMMENT ON FUNCTION public.create_profile_for_new_user() IS '自动为新注册用户创建资料';
COMMENT ON FUNCTION public.create_default_tags_for_new_user() IS '自动为新用户添加默认标签';
COMMENT ON FUNCTION public.update_profile_timestamp() IS '自动更新记录的时间戳';
COMMENT ON FUNCTION public.soft_delete_insight() IS '实现软删除功能';
