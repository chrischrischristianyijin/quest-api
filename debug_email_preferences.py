#!/usr/bin/env python3
"""
Comprehensive debug test for email preferences API
Run this and paste the console output to help debug the issue
"""
import requests
import json
import time
from datetime import datetime

# Test token from the frontend logs
TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjJTWkh3clV5YWRXQm5EaWwiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3dscGl0c3Rnam9teW56Zm5xa3llLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiZTkxZGFkZS0xODcyLTQ0NGQtYjBlNy0xODVmZjdlMDU0NWEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU4MjY5NjM0LCJpYXQiOjE3NTgxODMyMzQsImVtYWlsIjoic3RhbzA0MjkwNkBnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJuaWNrbmFtZSI6IkdhcnkiLCJ1c2VybmFtZSI6InN0YW8wNDI5MDZfMmI4NzllNzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc1ODE4MzIzNH1dLCJzZXNzaW9uX2lkIjoiNzlmZDBlMGItOWE5OS00NzRjLWI0YzQtMGRkMTk5MTlhMDYwIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.-7u2Y_WcJcxM7X8WDQ92repoTgqQ_1OLf5Rkxs9z5Dc"

BASE_URL = "https://quest-api-edz1.onrender.com"

def print_separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_token_validity():
    """Test if the token is still valid"""
    print_separator("TOKEN VALIDITY TEST")
    
    try:
        import jwt
        payload = jwt.decode(TOKEN, options={"verify_signature": False})
        
        current_time = int(time.time())
        exp_time = payload.get('exp', 0)
        
        print(f"📋 Token Info:")
        print(f"   Issuer: {payload.get('iss', 'Unknown')}")
        print(f"   Subject (User ID): {payload.get('sub', 'Unknown')}")
        print(f"   Email: {payload.get('email', 'Unknown')}")
        print(f"   Current time: {current_time} ({datetime.fromtimestamp(current_time)})")
        print(f"   Expiration: {exp_time} ({datetime.fromtimestamp(exp_time)})")
        print(f"   Time remaining: {exp_time - current_time} seconds")
        
        if exp_time < current_time:
            print("❌ TOKEN IS EXPIRED!")
            return False
        else:
            print("✅ Token is still valid")
            return True
            
    except Exception as e:
        print(f"❌ Failed to decode token: {e}")
        return False

def test_api_endpoint(endpoint, method="GET", data=None):
    """Test a specific API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"\n🔗 Testing {method} {endpoint}")
    print(f"   URL: {url}")
    print(f"   Headers: {json.dumps(headers, indent=4)}")
    
    if data:
        print(f"   Request Body: {json.dumps(data, indent=4)}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        else:
            print(f"❌ Unsupported method: {method}")
            return
        
        print(f"\n📊 Response:")
        print(f"   Status Code: {response.status_code}")
        print(f"   Status Text: {response.reason}")
        print(f"   Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"   Body (JSON): {json.dumps(response_json, indent=4)}")
        except:
            print(f"   Body (Text): {response.text}")
        
        if response.status_code == 200:
            print("✅ SUCCESS")
        elif response.status_code == 401:
            print("❌ AUTHENTICATION FAILED")
        elif response.status_code == 500:
            print("❌ SERVER ERROR")
        else:
            print(f"⚠️  UNEXPECTED STATUS: {response.status_code}")
            
        return response
        
    except requests.exceptions.Timeout:
        print("❌ REQUEST TIMEOUT (30s)")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ CONNECTION ERROR: {e}")
    except Exception as e:
        print(f"❌ REQUEST FAILED: {e}")

def test_all_email_endpoints():
    """Test all email-related endpoints"""
    print_separator("EMAIL API ENDPOINTS TEST")
    
    # Test 1: Get email preferences
    print("\n🧪 Test 1: GET /api/v1/email/preferences")
    get_response = test_api_endpoint("/api/v1/email/preferences", "GET")
    
    # Test 2: Update email preferences (if GET worked)
    if get_response and get_response.status_code == 200:
        print("\n🧪 Test 2: PUT /api/v1/email/preferences")
        update_data = {
            "weekly_digest_enabled": True,
            "preferred_day": 2,
            "preferred_hour": 10,
            "timezone": "America/New_York",
            "no_activity_policy": "brief"
        }
        test_api_endpoint("/api/v1/email/preferences", "PUT", update_data)
    else:
        print("\n⏭️  Skipping PUT test because GET failed")
    
    # Test 3: Preview digest
    print("\n🧪 Test 3: POST /api/v1/email/digest/preview")
    preview_data = {
        "user_id": "be91dade-1872-444d-b0e7-185ff7e0545a"
    }
    test_api_endpoint("/api/v1/email/digest/preview", "POST", preview_data)

def test_other_api_endpoints():
    """Test other API endpoints to see if the auth issue is specific to email API"""
    print_separator("OTHER API ENDPOINTS TEST")
    
    # Test user profile endpoint
    print("\n🧪 Test: GET /api/v1/user/profile")
    test_api_endpoint("/api/v1/user/profile", "GET")
    
    # Test insights endpoint  
    print("\n🧪 Test: GET /api/v1/insights/")
    test_api_endpoint("/api/v1/insights/", "GET")

def main():
    """Run all tests"""
    print("🚀 EMAIL PREFERENCES DEBUG TEST")
    print(f"🕐 Test started at: {datetime.now()}")
    print(f"🌐 Base URL: {BASE_URL}")
    
    # Test 1: Token validity
    if not test_token_validity():
        print("\n❌ Token is invalid, stopping tests")
        return
    
    # Test 2: Email API endpoints
    test_all_email_endpoints()
    
    # Test 3: Other API endpoints for comparison
    test_other_api_endpoints()
    
    print_separator("TEST SUMMARY")
    print("📋 Please copy and paste ALL the output above to help debug the issue!")
    print("🔍 Pay special attention to:")
    print("   - Any 401 authentication errors")
    print("   - Any 500 server errors with detailed messages")
    print("   - Differences between email API and other API responses")
    print("   - Any timeout or connection issues")

if __name__ == "__main__":
    main()
