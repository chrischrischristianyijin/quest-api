"""
Test script to verify email retrieval from auth.users works correctly
"""
import asyncio
import os
from dotenv import load_dotenv
from app.services.digest_repo import DigestRepo
from datetime import datetime, timezone

load_dotenv()

async def test_email_retrieval():
    """Test getting sendable users with proper email retrieval"""
    repo = DigestRepo()
    
    print("\n" + "="*60)
    print("Testing Email Retrieval from auth.users")
    print("="*60 + "\n")
    
    # Get sendable users
    now_utc = datetime.now(timezone.utc)
    users = await repo.get_sendable_users(now_utc)
    
    print(f"✅ Found {len(users)} users with weekly_digest_enabled=True\n")
    
    for i, user in enumerate(users, 1):
        print(f"{i}. User ID: {user['id']}")
        print(f"   Email: {user['email']}")
        print(f"   Name: {user['name']}")
        print(f"   Timezone: {user['timezone']}")
        print(f"   Preferred: Day {user['preferred_day']}, Hour {user['preferred_hour']}")
        print()
    
    if len(users) == 0:
        print("⚠️  No users found. Check if any users have weekly_digest_enabled=True")
    
    print("="*60)
    return users

if __name__ == "__main__":
    asyncio.run(test_email_retrieval())
