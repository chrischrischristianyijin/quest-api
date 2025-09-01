#!/usr/bin/env python3
"""
测试Google令牌格式解析
"""

def test_token_parsing():
    """测试令牌解析逻辑"""
    
    test_tokens = [
        "google_existing_user_123e4567-e89b-12d3-a456-426614174000_abc123",
        "google_auth_token_123e4567-e89b-12d3-a456-426614174000_def456", 
        "google_new_user_123e4567-e89b-12d3-a456-426614174000_ghi789"
    ]
    
    for token in test_tokens:
        print(f"\n测试令牌: {token}")
        
        user_id = None
        
        if token.startswith("google_existing_user_"):
            remaining = token[len("google_existing_user_"):]
            user_part_and_uuid = remaining.rsplit("_", 1)
            if len(user_part_and_uuid) == 2:
                user_id = user_part_and_uuid[0]
                print(f"✅ 从Google existing user令牌提取用户ID: {user_id}")
            else:
                user_id = remaining
                print(f"⚠️ 从Google existing user令牌提取用户ID(无uuid): {user_id}")
                
        elif token.startswith("google_auth_token_"):
            remaining = token[len("google_auth_token_"):]
            user_part_and_uuid = remaining.rsplit("_", 1)
            if len(user_part_and_uuid) == 2:
                user_id = user_part_and_uuid[0]
                print(f"✅ 从Google auth token令牌提取用户ID: {user_id}")
            else:
                user_id = remaining
                print(f"⚠️ 从Google auth token令牌提取用户ID(无uuid): {user_id}")
                
        elif token.startswith("google_new_user_"):
            remaining = token[len("google_new_user_"):]
            user_part_and_uuid = remaining.rsplit("_", 1)
            if len(user_part_and_uuid) == 2:
                user_id = user_part_and_uuid[0]
                print(f"✅ 从Google new user令牌提取用户ID: {user_id}")
            else:
                user_id = remaining
                print(f"⚠️ 从Google new user令牌提取用户ID(无uuid): {user_id}")
        else:
            print(f"❌ 未知的Google令牌格式")
            
        print(f"解析结果 - 用户ID: {user_id}")

if __name__ == "__main__":
    test_token_parsing()
