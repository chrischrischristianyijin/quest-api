-- 为现有用户添加预设标签
-- 这个脚本会为所有现有用户创建默认标签

-- 预设标签配置
DO $$
DECLARE
    user_record RECORD;
    tag_name TEXT;
    tag_color TEXT;
    tag_names TEXT[] := ARRAY['tech', 'design', 'business', 'lifestyle', 'education'];
    tag_colors TEXT[] := ARRAY['#65558F', '#65558F', '#65558F', '#65558F', '#65558F'];
BEGIN
    -- 遍历所有用户
    FOR user_record IN SELECT id FROM public.users LOOP
        -- 为每个用户创建预设标签
        FOR i IN 1..array_length(tag_names, 1) LOOP
            tag_name := tag_names[i];
            tag_color := tag_colors[i];
            
            -- 检查标签是否已存在
            IF NOT EXISTS (
                SELECT 1 FROM public.user_tags 
                WHERE user_id = user_record.id AND name = tag_name
            ) THEN
                -- 插入预设标签
                INSERT INTO public.user_tags (user_id, name, color)
                VALUES (user_record.id, tag_name, tag_color);
                
                RAISE NOTICE 'Created tag % for user %', tag_name, user_record.id;
            ELSE
                RAISE NOTICE 'Tag % already exists for user %', tag_name, user_record.id;
            END IF;
        END LOOP;
    END LOOP;
END $$;

-- 显示结果统计
SELECT 
    u.email,
    COUNT(ut.id) as tag_count
FROM public.users u
LEFT JOIN public.user_tags ut ON u.id = ut.user_id
GROUP BY u.id, u.email
ORDER BY u.created_at; 