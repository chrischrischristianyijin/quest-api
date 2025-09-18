#!/usr/bin/env python3
"""
Test script for the weekly digest system.
Run this to test the digest functionality without setting up a full cron job.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.digest_repo import DigestRepo
from app.services.digest_job import DigestJob, DigestJobConfig

async def test_digest_system():
    """Test the digest system with dry run."""
    print("🧪 Testing Quest Email Digest System")
    print("=" * 50)
    
    try:
        # Initialize repository
        print("📊 Initializing database connection...")
        repo = DigestRepo()
        
        # Configure job for testing
        config = DigestJobConfig(
            dry_run=True,  # Don't actually send emails
            batch_size=5,  # Small batch for testing
            max_retries=1
        )
        
        # Create job
        job = DigestJob(repo, config)
        
        print("🚀 Running digest sweep...")
        print(f"⏰ Current time: {datetime.now(timezone.utc).isoformat()}")
        print(f"🔧 Dry run mode: {config.dry_run}")
        print()
        
        # Run the sweep
        result = await job.run_sweep()
        
        # Display results
        print("📈 Results:")
        print(f"  ✅ Success: {result['success']}")
        print(f"  👥 Processed: {result.get('processed', 0)} users")
        print(f"  📧 Sent: {result.get('sent', 0)} emails")
        print(f"  ⏭️  Skipped: {result.get('skipped', 0)} users")
        print(f"  ❌ Failed: {result.get('failed', 0)} users")
        
        if result.get('errors'):
            print(f"  🚨 Errors: {len(result['errors'])}")
            for error in result['errors'][:3]:  # Show first 3 errors
                print(f"    - {error}")
        
        print()
        
        # Get some stats
        print("📊 System Statistics:")
        stats = await repo.get_digest_stats(7)
        print(f"  👥 Total users: {stats.get('total_users', 0)}")
        print(f"  📧 Digests sent (7 days): {stats.get('digests_sent', 0)}")
        print(f"  ❌ Digests failed (7 days): {stats.get('digests_failed', 0)}")
        
        print()
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_email_preferences():
    """Test email preferences functionality."""
    print("\n🔧 Testing Email Preferences")
    print("=" * 30)
    
    try:
        repo = DigestRepo()
        
        # Test getting sendable users
        print("👥 Fetching sendable users...")
        users = await repo.get_sendable_users(datetime.now(timezone.utc))
        print(f"  Found {len(users)} users with digest enabled")
        
        if users:
            user = users[0]
            print(f"  Example user: {user.get('email', 'unknown')}")
            print(f"    Timezone: {user.get('timezone', 'unknown')}")
            print(f"    Preferred day: {user.get('preferred_day', 'unknown')}")
            print(f"    Preferred hour: {user.get('preferred_hour', 'unknown')}")
        
        print("✅ Email preferences test completed!")
        
    except Exception as e:
        print(f"❌ Email preferences test failed: {e}")
        return False
    
    return True

async def test_content_generation():
    """Test content generation for a user."""
    print("\n📝 Testing Content Generation")
    print("=" * 35)
    
    try:
        from app.services.digest_content import DigestContentGenerator
        from app.services.digest_time import get_week_boundaries
        
        # Create test user data
        test_user = {
            "id": "test-user-123",
            "email": "test@example.com",
            "first_name": "Test",
            "timezone": "America/Los_Angeles"
        }
        
        # Create test insights
        test_insights = [
            {
                "id": "insight-1",
                "title": "Test Insight 1",
                "description": "This is a test insight",
                "url": "https://example.com/1",
                "created_at": "2024-01-15T10:00:00Z",
                "tags": ["test", "example"],
                "insight_contents": [{"summary": "This is a test summary"}]
            },
            {
                "id": "insight-2",
                "title": "Test Insight 2",
                "description": "Another test insight",
                "url": "https://example.com/2",
                "created_at": "2024-01-16T14:30:00Z",
                "tags": ["test"],
                "insight_contents": [{"summary": "Another test summary"}]
            }
        ]
        
        test_stacks = [
            {
                "id": "stack-1",
                "name": "Test Stack",
                "description": "A test stack",
                "item_count": 2,
                "created_at": "2024-01-15T09:00:00Z"
            }
        ]
        
        # Generate content
        generator = DigestContentGenerator()
        payload = generator.build_user_digest_payload(
            test_user, test_insights, test_stacks, "brief"
        )
        
        print(f"  📊 Generated payload for user: {test_user['first_name']}")
        print(f"  📝 Insights: {len(test_insights)}")
        print(f"  📚 Stacks: {len(test_stacks)}")
        print(f"  🎯 Activity summary: {payload['activity_summary']['total_activity']} activities")
        
        # Test different no-activity policies
        print("\n  🧪 Testing no-activity policies:")
        
        for policy in ["skip", "brief", "suggestions"]:
            empty_payload = generator.build_user_digest_payload(
                test_user, [], [], policy
            )
            print(f"    {policy}: {empty_payload['metadata'].get('reason', 'unknown')}")
        
        print("✅ Content generation test completed!")
        
    except Exception as e:
        print(f"❌ Content generation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def main():
    """Run all tests."""
    print("🚀 Starting Quest Email System Tests")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {missing_vars}")
        print("Please set these variables before running the test.")
        return False
    
    # Run tests
    tests = [
        ("Email Preferences", test_email_preferences),
        ("Content Generation", test_content_generation),
        ("Digest System", test_digest_system),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} test...")
        result = await test_func()
        results.append((test_name, result))
    
    # Summary
    print("\n📊 Test Summary")
    print("=" * 20)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Your email system is ready to go.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
    
    return passed == len(results)

if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

