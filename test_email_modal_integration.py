#!/usr/bin/env python3
"""
Test script to verify email modal integration with backend API.
This script tests the email API endpoints that the frontend modal will use.
"""

import asyncio
import httpx
import json
from datetime import datetime

# Test configuration
API_BASE_URL = "http://localhost:3001"
TEST_USER_ID = "test-user-123"
TEST_EMAIL = "test@example.com"

async def test_email_api():
    """Test all email API endpoints used by the modal."""
    
    async with httpx.AsyncClient() as client:
        print("🧪 Testing Email API Integration for Modal")
        print("=" * 50)
        
        # Test 1: Get email preferences (without auth for now)
        print("\n1. Testing GET /api/v1/email/preferences")
        try:
            response = await client.get(f"{API_BASE_URL}/api/v1/email/preferences")
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print("   ✅ Authentication required (expected)")
            else:
                print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 2: Update email preferences
        print("\n2. Testing PUT /api/v1/email/preferences")
        try:
            preferences_data = {
                "weekly_digest_enabled": True,
                "preferred_day": 1,
                "preferred_hour": 9,
                "timezone": "America/Los_Angeles",
                "no_activity_policy": "skip"
            }
            response = await client.put(
                f"{API_BASE_URL}/api/v1/email/preferences",
                json=preferences_data
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print("   ✅ Authentication required (expected)")
            else:
                print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 3: Preview digest
        print("\n3. Testing POST /api/v1/email/digest/preview")
        try:
            preview_data = {
                "user_id": TEST_USER_ID,
                "week_start": None
            }
            response = await client.post(
                f"{API_BASE_URL}/api/v1/email/digest/preview",
                json=preview_data
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print("   ✅ Authentication required (expected)")
            else:
                print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 4: Send test email
        print("\n4. Testing POST /api/v1/email/test")
        try:
            test_email_data = {
                "email": TEST_EMAIL
            }
            response = await client.post(
                f"{API_BASE_URL}/api/v1/email/test",
                json=test_email_data
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 401:
                print("   ✅ Authentication required (expected)")
            else:
                print(f"   Response: {response.json()}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 5: Health check
        print("\n5. Testing API Health")
        try:
            response = await client.get(f"{API_BASE_URL}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                health_data = response.json()
                print(f"   ✅ API is healthy: {health_data['status']}")
                print(f"   Database: {health_data.get('database', 'unknown')}")
            else:
                print(f"   ❌ API health check failed")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 50)
        print("🎯 Email Modal Integration Test Complete")
        print("\n📝 Notes:")
        print("- All endpoints require authentication (JWT token)")
        print("- Frontend modal will handle auth via api.js")
        print("- Email functionality requires BREVO_API_KEY in .env")
        print("- Modal provides fallback to localStorage if API fails")

if __name__ == "__main__":
    asyncio.run(test_email_api())
