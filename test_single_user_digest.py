"""
Test script to send digest to a single user
"""
import asyncio
import os
from dotenv import load_dotenv
from app.services.digest_repo import DigestRepo
from app.services.digest_job import DigestJob, DigestJobConfig
from datetime import datetime, timezone

load_dotenv()

async def test_single_user_digest(user_id: str):
    """Test sending digest to a specific user"""
    repo = DigestRepo()
    config = DigestJobConfig()
    job = DigestJob(repo, config)

    print("\n" + "="*60)
    print(f"Testing Digest for Single User: {user_id}")
    print("="*60 + "\n")

    # Get all sendable users first
    now_utc = datetime.now(timezone.utc)
    all_users = await repo.get_sendable_users(now_utc)

    # Find the specific user
    target_user = None
    for user in all_users:
        if user['id'] == user_id:
            target_user = user
            break

    if not target_user:
        print(f"❌ User {user_id} not found in sendable users list")
        print(f"   User might not have weekly_digest_enabled=True")
        return

    print(f"✅ Found user:")
    print(f"   ID: {target_user['id']}")
    print(f"   Email: {target_user['email']}")
    print(f"   Name: {target_user['name']}")
    print(f"   Timezone: {target_user['timezone']}")
    print(f"   Preferred: Day {target_user['preferred_day']}, Hour {target_user['preferred_hour']}\n")

    # Process just this user with force_send=True to bypass scheduling
    print("📧 Sending digest email...\n")
    result = await job._process_user(target_user, now_utc, force_send=True)

    print("="*60)
    print("Result:")
    print(f"   Status: {result.get('status')}")
    if result.get('reason'):
        print(f"   Reason: {result.get('reason')}")
    if result.get('error'):
        print(f"   Error: {result.get('error')}")
    if result.get('digest_id'):
        print(f"   Digest ID: {result.get('digest_id')}")
    print("="*60)

if __name__ == "__main__":
    user_id = "698fab66-6b42-48e3-86d5-115ad5478c71"
    asyncio.run(test_single_user_digest(user_id))
