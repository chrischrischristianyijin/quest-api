#!/usr/bin/env python3
"""
Comprehensive test for email services with authentication
"""
import asyncio
import httpx
import json
import os
from datetime import datetime, timezone

# Test configuration
BASE_URL = "https://quest-api-edz1.onrender.com"
TEST_EMAIL = "test@example.com"

# You'll need to get a valid JWT token for testing
# This could be from a login endpoint or a test token
TEST_JWT_TOKEN = os.getenv("TEST_JWT_TOKEN", "")

async def test_email_services():
    """Test the email services comprehensively"""
    
    print("🧪 Testing Quest Email Services (Comprehensive)")
    print("=" * 60)
    
    if not TEST_JWT_TOKEN:
        print("⚠️  No TEST_JWT_TOKEN provided. Some tests will be skipped.")
        print("   Set TEST_JWT_TOKEN environment variable to test authenticated endpoints.")
    
    headers = {
        "Authorization": f"Bearer {TEST_JWT_TOKEN}",
        "Content-Type": "application/json"
    } if TEST_JWT_TOKEN else {"Content-Type": "application/json"}
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Health check
        print("\n1. 🏥 Testing health check...")
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Health check passed")
            else:
                print("   ❌ Health check failed")
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
        
        # Test 2: Test email endpoint (requires auth)
        print("\n2. 📧 Testing email test endpoint...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/email/test",
                json={"email": TEST_EMAIL},
                headers=headers
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 200:
                print("   ✅ Test email sent successfully")
            elif response.status_code == 401:
                print("   ⚠️  Test email requires authentication")
            else:
                print("   ❌ Test email endpoint failed")
        except Exception as e:
            print(f"   ❌ Test email error: {e}")
        
        # Test 3: Email preferences (requires auth)
        print("\n3. ⚙️  Testing email preferences...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/email/preferences",
                headers=headers
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 200:
                print("   ✅ Email preferences retrieved successfully")
            elif response.status_code == 401:
                print("   ⚠️  Email preferences require authentication")
            else:
                print("   ❌ Email preferences failed")
        except Exception as e:
            print(f"   ❌ Email preferences error: {e}")
        
        # Test 4: Update email preferences (requires auth)
        print("\n4. 🔧 Testing email preferences update...")
        try:
            update_data = {
                "weekly_digest_enabled": True,
                "preferred_day": 1,  # Monday
                "preferred_hour": 9,  # 9 AM
                "timezone": "UTC",
                "no_activity_policy": "brief"
            }
            
            response = await client.put(
                f"{BASE_URL}/api/v1/email/preferences",
                json=update_data,
                headers=headers
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 200:
                print("   ✅ Email preferences updated successfully")
            elif response.status_code == 401:
                print("   ⚠️  Email preferences update requires authentication")
            else:
                print("   ❌ Email preferences update failed")
        except Exception as e:
            print(f"   ❌ Email preferences update error: {e}")
        
        # Test 5: Digest preview (requires auth)
        print("\n5. 👁️  Testing digest preview...")
        try:
            preview_data = {
                "user_id": "test-user-id",
                "week_start": "2024-01-01"
            }
            
            response = await client.post(
                f"{BASE_URL}/api/v1/email/digest/preview",
                json=preview_data,
                headers=headers
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                print("   ✅ Digest preview generated successfully")
            elif response.status_code == 401:
                print("   ⚠️  Digest preview requires authentication")
            else:
                print("   ❌ Digest preview failed")
        except Exception as e:
            print(f"   ❌ Digest preview error: {e}")
        
        # Test 6: Email stats (requires auth)
        print("\n6. 📊 Testing email stats...")
        try:
            response = await client.get(
                f"{BASE_URL}/api/v1/email/stats?days=7",
                headers=headers
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 200:
                print("   ✅ Email stats retrieved successfully")
            elif response.status_code == 401:
                print("   ⚠️  Email stats require authentication")
            else:
                print("   ❌ Email stats failed")
        except Exception as e:
            print(f"   ❌ Email stats error: {e}")
        
        # Test 7: Unsubscribe endpoint (no auth required)
        print("\n7. 🚫 Testing unsubscribe endpoint...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/email/unsubscribe",
                json={"token": "test-token"}
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 404:
                print("   ✅ Unsubscribe endpoint working (invalid token as expected)")
            else:
                print("   ⚠️  Unsubscribe endpoint response unexpected")
        except Exception as e:
            print(f"   ❌ Unsubscribe error: {e}")
        
        # Test 8: Check API documentation
        print("\n8. 📚 Testing API documentation...")
        try:
            response = await client.get(f"{BASE_URL}/docs")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ API documentation accessible")
                print("   📖 Check /docs for complete API reference")
            else:
                print("   ❌ API documentation not accessible")
        except Exception as e:
            print(f"   ❌ API documentation error: {e}")
        
        # Test 9: Test Brevo webhook endpoint
        print("\n9. 🔗 Testing Brevo webhook endpoint...")
        try:
            webhook_data = {
                "event": "delivered",
                "message-id": "test-message-id",
                "email": "test@example.com",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            response = await client.post(
                f"{BASE_URL}/api/v1/email/webhooks/brevo",
                json=webhook_data
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 200:
                print("   ✅ Brevo webhook endpoint working")
            else:
                print("   ❌ Brevo webhook endpoint failed")
        except Exception as e:
            print(f"   ❌ Brevo webhook error: {e}")

if __name__ == "__main__":
    asyncio.run(test_email_services())
