#!/usr/bin/env python3
"""
Test script for digest sending logic.
Demonstrates how to test the decision logic and Brevo sending.
"""
import asyncio
import httpx
import json
from datetime import datetime
import pytz

# Configuration
API_BASE_URL = "https://quest-api-edz1.onrender.com"  # Update with your API URL
TEST_EMAIL = "your-test@example.com"  # Update with your test email

async def test_digest_sending():
    """Test the digest sending logic end-to-end."""
    
    print("🧪 Testing Digest Sending Logic")
    print("=" * 50)
    
    # You'll need to get a valid auth token for testing
    # This is just a placeholder - replace with actual token
    auth_token = "YOUR_AUTH_TOKEN_HERE"
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Test 1: Dry run - decision only (no send)
        print("\n1️⃣ Testing dry run (decision only)...")
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/email/digest/test-send",
                params={"dry_run": True},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Dry run successful")
                print(f"   Decision: {data.get('decision')}")
                print(f"   Will send: {data.get('will_send')}")
                print(f"   Has insights: {data.get('stats', {}).get('has_insights')}")
                print(f"   Current time (UTC): {data.get('current_time_utc')}")
                print(f"   Current time (local): {data.get('current_time_local')}")
                print(f"   Note: {data.get('note')}")
            else:
                print(f"❌ Dry run failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Dry run error: {e}")
        
        # Test 2: Force dry run (build params but don't send)
        print("\n2️⃣ Testing force dry run...")
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/email/digest/test-send",
                params={"dry_run": True, "force": True},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Force dry run successful")
                print(f"   Decision: {data.get('decision')}")
                print(f"   Forced: {data.get('forced')}")
                print(f"   Will send: {data.get('will_send')}")
                print(f"   Params sample: {json.dumps(data.get('params_sample', {}), indent=2)}")
                print(f"   Note: {data.get('note')}")
            else:
                print(f"❌ Force dry run failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Force dry run error: {e}")
        
        # Test 3: Real send to test email (force, no schedule wait)
        print(f"\n3️⃣ Testing real send to {TEST_EMAIL}...")
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/email/digest/test-send",
                params={
                    "dry_run": False, 
                    "force": True, 
                    "email_override": TEST_EMAIL
                },
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Real send successful")
                print(f"   Decision: {data.get('decision')}")
                print(f"   Forced: {data.get('forced')}")
                print(f"   Will send: {data.get('will_send')}")
                print(f"   Send result: {json.dumps(data.get('send_result', {}), indent=2)}")
                
                # Check if we got a message ID
                send_result = data.get('send_result', {})
                if send_result.get('success') and send_result.get('message_id'):
                    print(f"📧 Email sent! Message ID: {send_result['message_id']}")
                    print(f"   Check your inbox at {TEST_EMAIL}")
                    print(f"   Check Brevo dashboard for delivery status")
                else:
                    print(f"❌ Send failed: {send_result.get('error', 'Unknown error')}")
            else:
                print(f"❌ Real send failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"❌ Real send error: {e}")
        
        # Test 4: Test with different timezone settings
        print("\n4️⃣ Testing timezone logic...")
        print("   (This would require updating user preferences first)")
        print("   You can test this by:")
        print("   1. Updating your email preferences to a specific timezone")
        print("   2. Setting preferred day/hour")
        print("   3. Calling the endpoint at the right time")
        print("   4. Or using force=true to bypass schedule")

def test_decision_logic():
    """Test the decision logic directly (no API calls)."""
    print("\n🧮 Testing Decision Logic Directly")
    print("=" * 50)
    
    from app.services.email_sender import EmailPrefs, should_send_weekly_digest
    
    # Test case 1: Tokyo timezone, Wednesday 22:00
    prefs = EmailPrefs(
        weekly_digest_enabled=True,
        preferred_day=2,  # Wednesday
        preferred_hour=22,  # 22:00
        timezone="Asia/Tokyo",
        no_activity_policy="skip"
    )
    
    # 22:00 JST is 13:00 UTC (no DST in Tokyo)
    now_utc = pytz.UTC.localize(datetime(2025, 9, 10, 13))  # Wednesday 13:00 UTC
    
    decision = should_send_weekly_digest(now_utc, prefs, has_insights=True)
    print(f"Tokyo Wednesday 22:00 (with insights): {decision}")
    
    decision_no_insights = should_send_weekly_digest(now_utc, prefs, has_insights=False)
    print(f"Tokyo Wednesday 22:00 (no insights, skip policy): {decision_no_insights}")
    
    # Test case 2: UTC timezone, Wednesday 14:00
    prefs_utc = EmailPrefs(
        weekly_digest_enabled=True,
        preferred_day=2,  # Wednesday
        preferred_hour=14,  # 14:00
        timezone="UTC",
        no_activity_policy="brief"
    )
    
    now_utc_2 = pytz.UTC.localize(datetime(2025, 9, 10, 14))  # Wednesday 14:00 UTC
    decision_utc = should_send_weekly_digest(now_utc_2, prefs_utc, has_insights=False)
    print(f"UTC Wednesday 14:00 (no insights, brief policy): {decision_utc}")
    
    # Test case 3: Wrong time
    now_wrong = pytz.UTC.localize(datetime(2025, 9, 10, 12))  # Wednesday 12:00 UTC
    decision_wrong = should_send_weekly_digest(now_wrong, prefs, has_insights=True)
    print(f"Tokyo Wednesday 21:00 (wrong hour): {decision_wrong}")

if __name__ == "__main__":
    print("🚀 Quest Digest Sending Test Suite")
    print("=" * 50)
    
    # Test decision logic directly
    test_decision_logic()
    
    # Test API endpoints (requires valid auth token)
    print("\n" + "=" * 50)
    print("⚠️  To test API endpoints, you need to:")
    print("1. Update API_BASE_URL with your actual API URL")
    print("2. Update TEST_EMAIL with your test email address")
    print("3. Update auth_token with a valid authentication token")
    print("4. Uncomment the line below to run API tests")
    print("=" * 50)
    
    # Uncomment to run API tests
    # asyncio.run(test_digest_sending())
