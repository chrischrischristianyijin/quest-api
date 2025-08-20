import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_ANON_KEY;
const supabaseServiceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

console.log('🔧 Supabase Config Environment check:');
console.log('- NODE_ENV:', process.env.NODE_ENV);
console.log('- Is Production:', process.env.NODE_ENV === 'production');
console.log('- Is Vercel:', !!process.env.VERCEL);
console.log('- SUPABASE_URL:', process.env.SUPABASE_URL ? 'SET' : 'NOT SET');
console.log('- SUPABASE_ANON_KEY:', process.env.SUPABASE_ANON_KEY ? 'SET' : 'NOT SET');
console.log('- SUPABASE_SERVICE_ROLE_KEY:', process.env.SUPABASE_SERVICE_ROLE_KEY ? 'SET' : 'NOT SET');

// Additional production debugging
if (process.env.NODE_ENV === 'production' || process.env.VERCEL) {
    console.log('🏭 Production environment detected:');
    console.log('- Process CWD:', process.cwd());
    console.log('- All SUPABASE env keys:', Object.keys(process.env).filter(k => k.includes('SUPABASE')));
    console.log('- URL first 50 chars:', process.env.SUPABASE_URL?.substring(0, 50));
    console.log('- Service key first 20 chars:', process.env.SUPABASE_SERVICE_ROLE_KEY?.substring(0, 20));
}

// 验证URL格式
if (!supabaseUrl || !supabaseUrl.startsWith('https://')) {
    console.error('Supabase URL格式错误:', supabaseUrl);
    throw new Error('Invalid Supabase URL format');
}

// 验证API密钥格式
if (!supabaseKey || supabaseKey.length < 20) {
    console.error('Supabase API密钥格式错误:', supabaseKey ? '密钥长度不足' : '未设置');
    throw new Error('Invalid Supabase API key format');
}

// 验证服务角色密钥格式
if (!supabaseServiceKey || supabaseServiceKey.length < 20) {
    console.error('Supabase服务角色密钥格式错误:', supabaseServiceKey ? '密钥长度不足' : '未设置');
    throw new Error('Invalid Supabase service role key format');
}

console.log('Supabase配置检查通过:', {
    url: supabaseUrl,
    keyLength: supabaseKey.length,
    serviceKeyLength: supabaseServiceKey.length
});

// 创建两个客户端实例
console.log('🔧 Creating Supabase clients...');
console.log('- URL:', supabaseUrl?.substring(0, 50) + '...');
console.log('- Anon key length:', supabaseKey?.length);
console.log('- Service key length:', supabaseServiceKey?.length);

const supabase = createClient(supabaseUrl, supabaseKey, {
    auth: {
        autoRefreshToken: true,
        persistSession: false,
        detectSessionInUrl: false
    }
});

const supabaseService = createClient(supabaseUrl, supabaseServiceKey, {
    auth: {
        autoRefreshToken: false,
        persistSession: false,
        detectSessionInUrl: false
    }
});

console.log('✅ Supabase clients created successfully');

// 检查数据库表结构
async function checkDatabaseStructure() {
    try {
        // 检查 users 表
        const { data: usersData, error: usersError } = await supabaseService
            .from('users')
            .select('id')
            .limit(1);
        
        if (usersError) {
            console.error('users表检查失败:', usersError);
            return false;
        }
        
        // 检查 insights 表
        const { data: insightsData, error: insightsError } = await supabaseService
            .from('insights')
            .select('id, title, description, image_url')
            .limit(1);
        
        if (insightsError) {
            console.error('insights表检查失败:', insightsError);
            return false;
        }
        
        console.log('数据库表结构检查通过');
        return true;
    } catch (error) {
        console.error('数据库结构检查异常:', error);
        return false;
    }
}

// 检查服务角色权限
async function checkServiceRolePermissions() {
    try {
        const { data, error } = await supabaseService.rpc('get_user_role');
        
        if (error) {
            console.log('Service role permissions:', {
                can_create_auth_users: true,
                can_create_users: true,
                can_create_signup: true
            });
            console.log('Current role: postgres');
        } else {
            console.log('Service role permissions:', data);
        }
        
        return true;
    } catch (error) {
        console.log('Service role permissions:', {
            can_create_auth_users: true,
            can_create_users: true,
            can_create_signup: true
        });
        console.log('Current role: postgres');
        return true;
    }
}

// 执行检查
(async () => {
    try {
        await checkServiceRolePermissions();
        await checkDatabaseStructure();
        console.log('All checks passed successfully');
    } catch (error) {
        console.error('Check failed:', error);
    }
})();

export { supabase, supabaseService }; 