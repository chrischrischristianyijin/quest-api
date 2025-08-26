
-- Quest API 注册问题修复脚本
-- 在 Supabase SQL 编辑器中运行此脚本

-- 1. 创建 profiles 表（如果不存在）
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    nickname TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    avatar_url TEXT,
    bio TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. 创建 user_tags 表（如果不存在）
CREATE TABLE IF NOT EXISTS public.user_tags (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#3B82F6',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- 3. 创建 insights 表（如果不存在）
CREATE TABLE IF NOT EXISTS public.insights (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT,
    url TEXT,
    image_url TEXT,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 4. 创建 insight_tags 表（如果不存在）
CREATE TABLE IF NOT EXISTS public.insight_tags (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    insight_id UUID NOT NULL REFERENCES public.insights(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES public.user_tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(insight_id, tag_id)
);

-- 5. 启用 RLS（Row Level Security）
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insight_tags ENABLE ROW LEVEL SECURITY;

-- 6. 创建 RLS 策略
-- profiles 表策略
CREATE POLICY "Users can view their own profile" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can insert their own profile" ON public.profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can update their own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

-- user_tags 表策略
CREATE POLICY "Users can view their own tags" ON public.user_tags
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own tags" ON public.user_tags
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own tags" ON public.user_tags
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own tags" ON public.user_tags
    FOR DELETE USING (auth.uid() = user_id);

-- insights 表策略
CREATE POLICY "Users can view their own insights" ON public.insights
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own insights" ON public.insights
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own insights" ON public.insights
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own insights" ON public.insights
    FOR DELETE USING (auth.uid() = user_id);

-- insight_tags 表策略
CREATE POLICY "Users can view insight tags" ON public.insight_tags
    FOR SELECT USING (true);

CREATE POLICY "Users can insert insight tags" ON public.insight_tags
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Users can delete insight tags" ON public.insight_tags
    FOR DELETE USING (true);

-- 7. 创建索引以提高性能
CREATE INDEX IF NOT EXISTS idx_profiles_email ON public.profiles(email);
CREATE INDEX IF NOT EXISTS idx_profiles_username ON public.profiles(username);
CREATE INDEX IF NOT EXISTS idx_user_tags_user_id ON public.user_tags(user_id);
CREATE INDEX IF NOT EXISTS idx_insights_user_id ON public.insights(user_id);
CREATE INDEX IF NOT EXISTS idx_insights_deleted_at ON public.insights(deleted_at);

-- 8. 创建触发器函数（如果不存在）
CREATE OR REPLACE FUNCTION public.create_profile_for_new_user()
RETURNS TRIGGER AS $$
DECLARE
    username_candidate TEXT;
    base_username TEXT;
    unique_suffix TEXT;
BEGIN
    -- 生成唯一用户名
    base_username := LOWER(REGEXP_REPLACE(NEW.email, '@.*', ''));
    base_username := REGEXP_REPLACE(base_username, '[^a-zA-Z0-9_]', '', 'g');
    
    IF base_username = '' THEN
        base_username := 'user';
    END IF;
    
    unique_suffix := SUBSTRING(MD5(NEW.email), 1, 8);
    username_candidate := base_username || '_' || unique_suffix;
    
    -- 插入 profile
    INSERT INTO public.profiles (id, username, email, nickname, created_at, updated_at)
    VALUES (NEW.id, username_candidate, NEW.email, 
            COALESCE(NEW.raw_user_meta_data->>'nickname', username_candidate),
            NOW(), NOW())
    ON CONFLICT (id) DO NOTHING;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 9. 创建触发器
DROP TRIGGER IF EXISTS create_profile_for_new_user ON auth.users;
CREATE TRIGGER create_profile_for_new_user
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION public.create_profile_for_new_user();

-- 10. 创建默认标签触发器
CREATE OR REPLACE FUNCTION public.create_default_tags_for_new_user()
RETURNS TRIGGER AS $$
BEGIN
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

DROP TRIGGER IF EXISTS create_default_tags_for_new_user ON public.profiles;
CREATE TRIGGER create_default_tags_for_new_user
AFTER INSERT ON public.profiles
FOR EACH ROW
EXECUTE FUNCTION public.create_default_tags_for_new_user();

-- 11. 创建时间戳更新触发器
CREATE OR REPLACE FUNCTION public.update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER update_profiles_timestamp
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW
    EXECUTE FUNCTION public.update_timestamp();

CREATE TRIGGER update_user_tags_timestamp
    BEFORE UPDATE ON public.user_tags
    FOR EACH ROW
    EXECUTE FUNCTION public.update_timestamp();

CREATE TRIGGER update_insights_timestamp
    BEFORE UPDATE ON public.insights
    FOR EACH ROW
    EXECUTE FUNCTION public.update_timestamp();

-- 12. 验证表创建
SELECT 'profiles' as table_name, COUNT(*) as row_count FROM public.profiles
UNION ALL
SELECT 'user_tags' as table_name, COUNT(*) as row_count FROM public.user_tags
UNION ALL
SELECT 'insights' as table_name, COUNT(*) as row_count FROM public.insights;

-- 完成！现在应该可以正常注册了
