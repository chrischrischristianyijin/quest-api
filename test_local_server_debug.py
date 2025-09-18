#!/usr/bin/env python3
"""
Test script for local server debugging - triggers actual error messages in console
Run this against your local server to see real error details
"""
import requests
import json
import time
from datetime import datetime

# Configuration for LOCAL server
LOCAL_API_BASE_URL = "http://localhost:8000"  # Adjust port as needed
PRODUCTION_API_BASE_URL = "https://quest-api-edz1.onrender.com"

USER_ID = "be91dade-1872-444d-b0e7-185ff7e0545a"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjJTWkh3clV5YWRXQm5EaWwiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3dscGl0c3Rnam9teW56Zm5xa3llLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiZTkxZGFkZS0xODcyLTQ0NGQtYjBlNy0xODVmZjdlMDU0NWEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU4MjY5NjM0LCJpYXQiOjE3NTgxODMyMzQsImVtYWlsIjoic3RhbzA0MjkwNkBnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJuaWNrbmFtZSI6IkdhcnkiLCJ1c2VybmFtZSI6InN0YW8wNDI5MDZfMmI4NzllNzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc1ODE4MzIzNH1dLCJzZXNzaW9uX2lkIjoiNzlmZDBlMGItOWE5OS00NzRjLWI0YzQtMGRkMTk5MTlhMDYwIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.-7u2Y_WcJcxM7X8WDQ92repoTgqQ_1OLf5Rkxs9z5Dc"

def test_local_endpoint(api_base_url, endpoint, method="GET", data=None, description="", delay=1):
    """Test endpoint and show what error messages appear in local server console"""
    print(f"\n{'='*70}")
    print(f"🧪 {description}")
    print(f"🌐 Server: {api_base_url}")
    print(f"{'='*70}")
    
    url = f"{api_base_url}{endpoint}"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"📍 URL: {url}")
    print(f"🔑 Method: {method}")
    if data:
        print(f"📤 Request Body:")
        print(json.dumps(data, indent=2))
    
    print(f"\n⏰ Making request in {delay} seconds...")
    print(f"👀 CHECK YOUR LOCAL SERVER CONSOLE FOR ERROR MESSAGES!")
    time.sleep(delay)
    
    try:
        print(f"🚀 Sending request NOW...")
        
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        
        print(f"\n📊 Response Status: {response.status_code} {response.reason}")
        
        try:
            response_json = response.json()
            print(f"📄 Response Body:")
            print(json.dumps(response_json, indent=2))
        except:
            print(f"📄 Raw Response:")
            print(response.text[:1000])
        
        if response.status_code >= 400:
            print(f"\n❌ ERROR DETECTED!")
            print(f"👀 Check your local server console for detailed error messages")
            print(f"🔍 Look for Python tracebacks, logger.error() messages, etc.")
        
        return response
        
    except requests.exceptions.ConnectionError:
        print(f"❌ CONNECTION ERROR - Is your local server running?")
        print(f"💡 Make sure you started the server with: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        return None
    except Exception as e:
        print(f"❌ REQUEST ERROR: {e}")
        return None

def check_server_availability(api_base_url):
    """Check if server is available"""
    try:
        response = requests.get(f"{api_base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Server at {api_base_url} is available")
            return True
        else:
            print(f"⚠️ Server at {api_base_url} returned {response.status_code}")
            return False
    except:
        print(f"❌ Server at {api_base_url} is not available")
        return False

def main():
    print("🔍 LOCAL SERVER DEBUGGING TEST")
    print(f"🕐 Started at: {datetime.now()}")
    print(f"👤 User ID: {USER_ID}")
    
    print(f"\n{'🏠 LOCAL SERVER SETUP INSTRUCTIONS':=^70}")
    print("""
    1. Open a terminal in your quest-api directory
    2. Activate your Python environment (if using one)
    3. Install dependencies: pip install -r requirements.txt
    4. Start the server: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    5. Keep that terminal open to see error messages
    6. Run this test script in another terminal
    """)
    
    # Check server availability
    print(f"\n{'🔍 SERVER AVAILABILITY CHECK':=^70}")
    
    local_available = check_server_availability(LOCAL_API_BASE_URL)
    prod_available = check_server_availability(PRODUCTION_API_BASE_URL)
    
    if not local_available and not prod_available:
        print("❌ Neither local nor production server is available")
        return
    
    # Choose which server to test
    if local_available:
        api_base_url = LOCAL_API_BASE_URL
        print(f"✅ Using LOCAL server: {api_base_url}")
        print(f"👀 WATCH YOUR LOCAL SERVER CONSOLE FOR ERROR MESSAGES!")
    else:
        api_base_url = PRODUCTION_API_BASE_URL
        print(f"⚠️ Using PRODUCTION server: {api_base_url}")
        print(f"📝 Production server won't show detailed error messages")
    
    input(f"\n🔄 Press ENTER when you're ready to start testing...")
    
    # Test 1: Basic working endpoint
    print(f"\n{'✅ TEST 1: WORKING ENDPOINT (BASELINE)':=^70}")
    test_local_endpoint(
        api_base_url,
        "/api/v1/user/profile",
        "GET",
        description="User Profile (should work)",
        delay=2
    )
    
    # Test 2: Email preferences
    print(f"\n{'📧 TEST 2: EMAIL PREFERENCES':=^70}")
    test_local_endpoint(
        api_base_url,
        "/api/v1/email/preferences",
        "GET",
        description="Email Preferences (should work)",
        delay=2
    )
    
    # Test 3: The failing digest preview
    print(f"\n{'❌ TEST 3: FAILING DIGEST PREVIEW':=^70}")
    print(f"👀 THIS IS THE MAIN TEST - WATCH YOUR CONSOLE CAREFULLY!")
    test_local_endpoint(
        api_base_url,
        "/api/v1/email/digest/preview",
        "POST",
        data={"user_id": USER_ID},
        description="Digest Preview (FAILING - check console for errors)",
        delay=3
    )
    
    # Test 4: Digest preview with different parameters
    print(f"\n{'🔍 TEST 4: DIGEST PREVIEW WITH WEEK START':=^70}")
    test_local_endpoint(
        api_base_url,
        "/api/v1/email/digest/preview",
        "POST",
        data={
            "user_id": USER_ID,
            "week_start": "2025-09-16"
        },
        description="Digest Preview with week_start (check console)",
        delay=2
    )
    
    # Test 5: HTML digest preview
    print(f"\n{'📄 TEST 5: HTML DIGEST PREVIEW':=^70}")
    test_local_endpoint(
        api_base_url,
        "/api/v1/email/digest/preview",
        "GET",
        description="HTML Digest Preview (check console)",
        delay=2
    )
    
    # Test 6: Update preferences and retry
    print(f"\n{'🔄 TEST 6: UPDATE PREFERENCES AND RETRY':=^70}")
    
    # First update preferences
    test_local_endpoint(
        api_base_url,
        "/api/v1/email/preferences",
        "PUT",
        data={
            "weekly_digest_enabled": True,
            "preferred_day": 1,
            "preferred_hour": 9,
            "timezone": "America/Los_Angeles",
            "no_activity_policy": "brief"
        },
        description="Update preferences to brief policy",
        delay=2
    )
    
    # Then retry digest preview
    test_local_endpoint(
        api_base_url,
        "/api/v1/email/digest/preview",
        "POST",
        data={"user_id": USER_ID},
        description="Digest Preview after preference update (check console)",
        delay=2
    )
    
    print(f"\n{'✅ LOCAL DEBUGGING TEST COMPLETED':=^70}")
    print(f"🕐 Finished at: {datetime.now()}")
    
    print(f"\n📋 What to Look For in Your Local Server Console:")
    print("   🔍 Python tracebacks showing exact line where error occurs")
    print("   📝 logger.error() messages with detailed error info")
    print("   🗄️ Database query errors or connection issues")
    print("   🧩 Content generation errors")
    print("   📧 Template rendering errors")
    print("   ⚠️ Any warnings or exceptions during digest creation")
    
    print(f"\n💡 Common Error Patterns to Look For:")
    print("   - KeyError: Missing required field in data")
    print("   - AttributeError: Calling method on None object")
    print("   - TypeError: Wrong data type passed to function")
    print("   - Database connection or query errors")
    print("   - Template rendering failures")

if __name__ == "__main__":
    main()
