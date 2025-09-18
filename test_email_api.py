#!/usr/bin/env python3
"""
Test script for email API endpoints
"""
import asyncio
import httpx
import json

# Test configuration
BASE_URL = "https://quest-api-edz1.onrender.com"
TEST_EMAIL = "test@example.com"

async def test_email_endpoints():
    """Test the email API endpoints"""
    
    print("🧪 Testing Quest Email API Endpoints")
    print("=" * 50)
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Health check
        print("\n1. Testing health check...")
        try:
            response = await client.get(f"{BASE_URL}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Health check passed")
            else:
                print("   ❌ Health check failed")
        except Exception as e:
            print(f"   ❌ Health check error: {e}")
        
        # Test 2: Test email endpoint (without auth for now)
        print("\n2. Testing email test endpoint...")
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/email/test",
                json={"email": TEST_EMAIL}
            )
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 200:
                print("   ✅ Test email endpoint accessible")
            elif response.status_code == 401:
                print("   ✅ Test email endpoint requires auth (expected)")
            else:
                print("   ❌ Test email endpoint failed")
        except Exception as e:
            print(f"   ❌ Test email error: {e}")
        
        # Test 3: Email preferences endpoint (should require auth)
        print("\n3. Testing email preferences endpoint...")
        try:
            response = await client.get(f"{BASE_URL}/api/v1/email/preferences")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 401:
                print("   ✅ Email preferences properly protected (requires auth)")
            else:
                print("   ⚠️  Email preferences not properly protected")
        except Exception as e:
            print(f"   ❌ Email preferences error: {e}")
        
        # Test 4: Check if email router is registered
        print("\n4. Testing email router registration...")
        try:
            response = await client.get(f"{BASE_URL}/docs")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ API docs accessible - check /docs for email endpoints")
            else:
                print("   ❌ API docs not accessible")
        except Exception as e:
            print(f"   ❌ API docs error: {e}")

if __name__ == "__main__":
    asyncio.run(test_email_endpoints())
