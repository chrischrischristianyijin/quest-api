-- 创建用户自定义标签表
CREATE TABLE IF NOT EXISTS public.user_tags (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id uuid REFERENCES public.users(id) ON DELETE CASCADE,
    name text NOT NULL,
    color text DEFAULT '#65558F',
    created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(user_id, name)
);

-- 添加索引
CREATE INDEX IF NOT EXISTS user_tags_user_id_idx ON public.user_tags(user_id);
CREATE INDEX IF NOT EXISTS user_tags_name_idx ON public.user_tags(name);

-- 启用RLS
ALTER TABLE public.user_tags ENABLE ROW LEVEL SECURITY;

-- RLS策略
CREATE POLICY "Users can view their own tags"
    ON public.user_tags FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own tags"
    ON public.user_tags FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own tags"
    ON public.user_tags FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own tags"
    ON public.user_tags FOR DELETE
    USING (auth.uid() = user_id);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_user_tags_updated_at 
    BEFORE UPDATE ON public.user_tags 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column(); 