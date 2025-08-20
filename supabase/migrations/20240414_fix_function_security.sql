-- 修复函数安全问题
-- 为所有函数设置明确的 search_path

-- 修复 update_follow_counts 函数
CREATE OR REPLACE FUNCTION update_follow_counts()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- Increase following count for follower
        UPDATE public.users 
        SET following_count = following_count + 1,
            updated_at = NOW()
        WHERE id = NEW.follower_id;
        
        -- Increase followers count for followed user
        UPDATE public.users 
        SET followers_count = followers_count + 1,
            updated_at = NOW()
        WHERE id = NEW.following_id;
        
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        -- Decrease following count for follower
        UPDATE public.users 
        SET following_count = following_count - 1,
            updated_at = NOW()
        WHERE id = OLD.follower_id;
        
        -- Decrease followers count for followed user
        UPDATE public.users 
        SET followers_count = followers_count - 1,
            updated_at = NOW()
        WHERE id = OLD.following_id;
        
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 修复 update_updated_at_column 函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 创建安全的用户处理函数（如果不存在）
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    -- 为新用户设置默认值
    NEW.updated_at = NOW();
    
    -- 可以在这里添加其他新用户处理逻辑
    -- 例如：设置默认头像、创建默认标签等
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 为新用户创建触发器（如果不存在）
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'handle_new_user_trigger'
    ) THEN
        CREATE TRIGGER handle_new_user_trigger
            BEFORE INSERT ON public.users
            FOR EACH ROW
            EXECUTE FUNCTION handle_new_user();
    END IF;
END $$; 