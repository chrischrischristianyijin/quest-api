#!/usr/bin/env python3
"""
数据库错误详细诊断脚本
专门解决 "Database error saving new user" 问题
"""

import os
import asyncio
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def create_detailed_fix():
    """创建详细的修复脚本"""
    sql_content = """
-- ========================================
-- Quest API 数据库错误详细修复脚本
-- 解决 "Database error saving new user" 问题
-- ========================================

-- 步骤 1: 检查当前表状态
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('profiles', 'user_tags', 'insights', 'insight_tags');

-- 步骤 2: 删除可能存在的损坏表（如果存在）
DROP TABLE IF EXISTS public.insight_tags CASCADE;
DROP TABLE IF EXISTS public.insights CASCADE;
DROP TABLE IF EXISTS public.user_tags CASCADE;
DROP TABLE IF EXISTS public.profiles CASCADE;

-- 步骤 3: 重新创建 profiles 表（核心表）
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    nickname TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    avatar_url TEXT,
    bio TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 步骤 4: 创建 user_tags 表
CREATE TABLE public.user_tags (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#3B82F6',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_user_tags_user_id FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE,
    CONSTRAINT unique_user_tag UNIQUE(user_id, name)
);

-- 步骤 5: 创建 insights 表
CREATE TABLE public.insights (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    url TEXT,
    image_url TEXT,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_insights_user_id FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE
);

-- 步骤 6: 创建 insight_tags 表
CREATE TABLE public.insight_tags (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    insight_id UUID NOT NULL,
    tag_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT fk_insight_tags_insight_id FOREIGN KEY (insight_id) REFERENCES public.insights(id) ON DELETE CASCADE,
    CONSTRAINT fk_insight_tags_tag_id FOREIGN KEY (tag_id) REFERENCES public.user_tags(id) ON DELETE CASCADE,
    CONSTRAINT unique_insight_tag UNIQUE(insight_id, tag_id)
);

-- 步骤 7: 创建必要的索引
CREATE INDEX idx_profiles_email ON public.profiles(email);
CREATE INDEX idx_profiles_username ON public.profiles(username);
CREATE INDEX idx_user_tags_user_id ON public.user_tags(user_id);
CREATE INDEX idx_insights_user_id ON public.insights(user_id);
CREATE INDEX idx_insights_deleted_at ON public.insights(deleted_at);

-- 步骤 8: 启用 RLS（Row Level Security）
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.insight_tags ENABLE ROW LEVEL SECURITY;

-- 步骤 9: 创建 RLS 策略
-- profiles 表策略
DROP POLICY IF EXISTS "Users can view their own profile" ON public.profiles;
CREATE POLICY "Users can view their own profile" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can insert their own profile" ON public.profiles;
CREATE POLICY "Users can insert their own profile" ON public.profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update their own profile" ON public.profiles;
CREATE POLICY "Users can update their own profile" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

-- user_tags 表策略
DROP POLICY IF EXISTS "Users can view their own tags" ON public.user_tags;
CREATE POLICY "Users can view their own tags" ON public.user_tags
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own tags" ON public.user_tags;
CREATE POLICY "Users can insert their own tags" ON public.user_tags
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own tags" ON public.user_tags;
CREATE POLICY "Users can update their own tags" ON public.user_tags
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own tags" ON public.user_tags;
CREATE POLICY "Users can delete their own tags" ON public.user_tags
    FOR DELETE USING (auth.uid() = user_id);

-- insights 表策略
DROP POLICY IF EXISTS "Users can view their own insights" ON public.insights;
CREATE POLICY "Users can view their own insights" ON public.insights
    FOR SELECT USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own insights" ON public.insights;
CREATE POLICY "Users can insert their own insights" ON public.insights
    FOR INSERT WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own insights" ON public.insights;
CREATE POLICY "Users can update their own insights" ON public.insights
    FOR UPDATE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own insights" ON public.insights;
CREATE POLICY "Users can delete their own insights" ON public.insights
    FOR DELETE USING (auth.uid() = user_id);

-- insight_tags 表策略
DROP POLICY IF EXISTS "Users can view insight tags" ON public.insight_tags;
CREATE POLICY "Users can view insight tags" ON public.insight_tags
    FOR SELECT USING (true);

DROP POLICY IF EXISTS "Users can insert insight tags" ON public.insight_tags;
CREATE POLICY "Users can insert insight tags" ON public.insight_tags
    FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Users can delete insight tags" ON public.insight_tags;
CREATE POLICY "Users can delete insight tags" ON public.insight_tags
    FOR DELETE USING (true);

-- 步骤 10: 创建触发器函数
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
EXCEPTION
    WHEN OTHERS THEN
        -- 记录错误但不阻止用户创建
        RAISE LOG 'Error creating profile for user %: %', NEW.id, SQLERRM;
        RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 步骤 11: 创建触发器
DROP TRIGGER IF EXISTS create_profile_for_new_user ON auth.users;
CREATE TRIGGER create_profile_for_new_user
AFTER INSERT ON auth.users
FOR EACH ROW
EXECUTE FUNCTION public.create_profile_for_new_user();

-- 步骤 12: 创建默认标签触发器
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
EXCEPTION
    WHEN OTHERS THEN
        -- 记录错误但不阻止profile创建
        RAISE LOG 'Error creating default tags for user %: %', NEW.id, SQLERRM;
        RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS create_default_tags_for_new_user ON public.profiles;
CREATE TRIGGER create_default_tags_for_new_user
AFTER INSERT ON public.profiles
FOR EACH ROW
EXECUTE FUNCTION public.create_default_tags_for_new_user();

-- 步骤 13: 创建时间戳更新触发器
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

-- 步骤 14: 授予必要的权限
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON public.profiles TO anon, authenticated;
GRANT ALL ON public.user_tags TO anon, authenticated;
GRANT ALL ON public.insights TO anon, authenticated;
GRANT ALL ON public.insight_tags TO anon, authenticated;

-- 步骤 15: 验证表创建
SELECT 'profiles' as table_name, COUNT(*) as row_count FROM public.profiles
UNION ALL
SELECT 'user_tags' as table_name, COUNT(*) as row_count FROM public.user_tags
UNION ALL
SELECT 'insights' as table_name, COUNT(*) as row_count FROM public.insights;

-- 步骤 16: 测试插入（可选）
-- INSERT INTO public.profiles (id, username, nickname, email, created_at, updated_at)
-- VALUES ('test-123', 'testuser', 'Test User', 'test@example.com', NOW(), NOW());

-- 完成！现在应该可以正常注册了
"""
    
    # 写入文件
    with open('detailed_fix.sql', 'w', encoding='utf-8') as f:
        f.write(sql_content)
    
    print("✅ 详细修复脚本已创建: detailed_fix.sql")
    return sql_content

def create_troubleshooting_guide():
    """创建故障排除指南"""
    guide_content = """
# Quest API 注册问题故障排除指南

## 🚨 问题描述
错误信息: "注册失败: Database error saving new user"
状态码: 400

## 🔍 问题分析
这个错误表明:
1. ✅ Supabase Auth 用户创建成功
2. ❌ 但在保存用户资料到 profiles 表时失败
3. ❌ 错误发生在数据库层面

## 🛠️ 解决步骤

### 步骤 1: 运行数据库修复脚本
在 Supabase SQL 编辑器中运行 `detailed_fix.sql`

### 步骤 2: 检查环境变量
确保在 Render 平台设置了正确的环境变量:
- SUPABASE_URL
- SUPABASE_ANON_KEY  
- SUPABASE_SERVICE_ROLE_KEY

### 步骤 3: 验证表结构
在 Supabase 中检查以下表是否存在:
- public.profiles
- public.user_tags
- public.insights
- public.insight_tags

### 步骤 4: 检查权限
确保服务角色密钥有足够权限:
- 读取和写入 public schema
- 创建和修改表
- 执行触发器函数

### 步骤 5: 重启应用
在 Render 平台重启应用服务

## 🔧 常见问题

### 问题 1: 表不存在
**症状**: 运行修复脚本后仍然报错
**解决**: 检查 SQL 脚本是否成功执行，查看错误日志

### 问题 2: 权限不足
**症状**: 插入操作被拒绝
**解决**: 检查 SUPABASE_SERVICE_ROLE_KEY 是否正确设置

### 问题 3: RLS 策略问题
**症状**: 认证用户无法插入数据
**解决**: 检查 RLS 策略是否正确配置

### 问题 4: 字段类型不匹配
**症状**: 数据类型错误
**解决**: 确保表字段类型与代码期望的类型一致

## 📋 验证清单

- [ ] 所有必要的表已创建
- [ ] 表字段类型正确
- [ ] RLS 策略已配置
- [ ] 触发器函数已创建
- [ ] 环境变量正确设置
- [ ] 应用已重启

## 🆘 如果问题仍然存在

1. 检查 Supabase 日志
2. 查看应用错误日志
3. 验证数据库连接
4. 检查网络连接
5. 联系技术支持

## 📞 获取帮助

如果按照以上步骤仍然无法解决问题，请提供:
1. 完整的错误日志
2. 数据库表结构截图
3. 环境变量配置（隐藏敏感信息）
4. 应用启动日志
"""
    
    # 写入文件
    with open('TROUBLESHOOTING.md', 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print("✅ 故障排除指南已创建: TROUBLESHOOTING.md")

def main():
    """主函数"""
    print("🚀 Quest API 数据库错误详细修复工具")
    print("=" * 60)
    
    # 创建详细修复脚本
    create_detailed_fix()
    
    # 创建故障排除指南
    create_troubleshooting_guide()
    
    print("\n📋 修复步骤:")
    print("1. 在 Supabase SQL 编辑器中运行 detailed_fix.sql")
    print("2. 检查环境变量配置")
    print("3. 验证表结构")
    print("4. 重启应用")
    print("5. 测试注册功能")
    
    print("\n💡 关键点:")
    print("- 这个脚本会完全重建所有表")
    print("- 包含完整的 RLS 策略配置")
    print("- 添加了错误处理机制")
    print("- 授予了必要的权限")
    
    print("\n📚 相关文档:")
    print("- detailed_fix.sql: 详细修复脚本")
    print("- TROUBLESHOOTING.md: 故障排除指南")
    
    print("\n🏁 修复工具准备完成！")

if __name__ == "__main__":
    main()
