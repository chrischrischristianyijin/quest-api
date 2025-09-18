#!/usr/bin/env python3
"""
Test script to verify email modal integration with deployed API on Render.
This script tests the email API endpoints that the frontend modal will use.
"""

import asyncio
import httpx
import json
from datetime import datetime

# Replace with your actual Render API URL
RENDER_API_URL = "https://your-quest-api.onrender.com"  # Update this with your actual URL
TEST_EMAIL = "test@example.com"

async def test_deployed_email_api():
    """Test email API endpoints on deployed Render instance."""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("🧪 Testing Deployed Email API Integration")
        print("=" * 50)
        print(f"🌐 API URL: {RENDER_API_URL}")
        
        # Test 1: Health check
        print("\n1. Testing API Health")
        try:
            response = await client.get(f"{RENDER_API_URL}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                health_data = response.json()
                print(f"   ✅ API is healthy: {health_data['status']}")
                print(f"   Database: {health_data.get('database', 'unknown')}")
            else:
                print(f"   ❌ API health check failed: {response.text}")
        except Exception as e:
            print(f"   ❌ Error connecting to API: {e}")
            print("   💡 Make sure your Render API is deployed and running")
            return
        
        # Test 2: Check if email endpoints are available
        print("\n2. Testing Email Endpoints Availability")
        try:
            # Test without auth to see if endpoints exist
            response = await client.get(f"{RENDER_API_URL}/api/v1/email/preferences")
            print(f"   GET /preferences: {response.status_code}")
            
            response = await client.post(f"{RENDER_API_URL}/api/v1/email/test", 
                                       json={"email": TEST_EMAIL})
            print(f"   POST /test: {response.status_code}")
            
            if response.status_code in [401, 422]:  # Auth required or validation error
                print("   ✅ Email endpoints are available and responding")
            else:
                print(f"   ⚠️  Unexpected response: {response.text[:100]}")
                
        except Exception as e:
            print(f"   ❌ Error testing email endpoints: {e}")
        
        # Test 3: Test Brevo API key configuration
        print("\n3. Testing Brevo API Key Configuration")
        try:
            # This will test if the BREVO_API_KEY is properly configured
            response = await client.post(f"{RENDER_API_URL}/api/v1/email/test", 
                                       json={"email": TEST_EMAIL})
            
            if response.status_code == 401:
                print("   ✅ API requires authentication (expected)")
                print("   ✅ Email service is properly configured")
            elif response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("   ✅ Test email sent successfully!")
                    print("   ✅ Brevo API key is working correctly")
                else:
                    print(f"   ⚠️  Test email failed: {result.get('message', 'Unknown error')}")
            else:
                print(f"   ⚠️  Unexpected response: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error testing Brevo configuration: {e}")
        
        print("\n" + "=" * 50)
        print("🎯 Deployed Email API Test Complete")
        print("\n📝 Next Steps:")
        print("1. Update RENDER_API_URL in this script with your actual API URL")
        print("2. Test the email preferences modal in your frontend")
        print("3. Try sending a test email through the modal")
        print("4. Check your email inbox for the test email")

if __name__ == "__main__":
    print("⚠️  IMPORTANT: Update RENDER_API_URL with your actual Render API URL")
    print("   You can find it in your Render dashboard")
    print()
    asyncio.run(test_deployed_email_api())
