"""
Test script to send digest to specific users by email
"""
import asyncio
import os
from dotenv import load_dotenv
from app.services.digest_repo import DigestRepo
from app.services.digest_job import DigestJob, DigestJobConfig
from datetime import datetime, timezone

load_dotenv()

async def test_multiple_users_digest(target_emails: list):
    """Test sending digest to specific users by email"""
    repo = DigestRepo()
    config = DigestJobConfig()
    job = DigestJob(repo, config)

    print("\n" + "="*60)
    print(f"Testing Digest for Users: {', '.join(target_emails)}")
    print("="*60 + "\n")

    # Get all sendable users first
    now_utc = datetime.now(timezone.utc)
    all_users = await repo.get_sendable_users(now_utc)

    # Find the specific users by email
    target_users = []
    for user in all_users:
        if user['email'] in target_emails:
            target_users.append(user)
            print(f"✅ Found user:")
            print(f"   ID: {user['id']}")
            print(f"   Email: {user['email']}")
            print(f"   Name: {user['name']}")
            print(f"   Timezone: {user['timezone']}")
            print(f"   Preferred: Day {user['preferred_day']}, Hour {user['preferred_hour']}\n")

    if len(target_users) == 0:
        print(f"❌ No users found with emails: {target_emails}")
        print(f"   Users might not have weekly_digest_enabled=True")
        return

    print(f"Found {len(target_users)} out of {len(target_emails)} requested users\n")
    print("="*60)

    # Process each user with force_send=True to bypass scheduling
    for i, user in enumerate(target_users, 1):
        print(f"\n📧 [{i}/{len(target_users)}] Sending digest to {user['email']}...")
        result = await job._process_user(user, now_utc, force_send=True)
        
        print(f"   Status: {result.get('status')}")
        if result.get('reason'):
            print(f"   Reason: {result.get('reason')}")
        if result.get('error'):
            print(f"   Error: {result.get('error')}")
        if result.get('digest_id'):
            print(f"   Digest ID: {result.get('digest_id')}")

    print("\n" + "="*60)
    print("✅ Test completed!")
    print("="*60)

if __name__ == "__main__":
    target_emails = [
        "tianyijin@berkeley.edu",
        "stao042906@gmail.com"
    ]
    asyncio.run(test_multiple_users_digest(target_emails))
