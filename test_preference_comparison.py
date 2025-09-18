#!/usr/bin/env python3
"""
Test to compare email preferences API vs digest preview preferences
"""
import requests
import json
from datetime import datetime

# Configuration
API_BASE_URL = "https://quest-api-edz1.onrender.com"
USER_ID = "be91dade-1872-444d-b0e7-185ff7e0545a"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjJTWkh3clV5YWRXQm5EaWwiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3dscGl0c3Rnam9teW56Zm5xa3llLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiZTkxZGFkZS0xODcyLTQ0NGQtYjBlNy0xODVmZjdlMDU0NWEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU4MjY5NjM0LCJpYXQiOjE3NTgxODMyMzQsImVtYWlsIjoic3RhbzA0MjkwNkBnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJuaWNrbmFtZSI6IkdhcnkiLCJ1c2VybmFtZSI6InN0YW8wNDI5MDZfMmI4NzllNzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc1ODE4MzIzNH1dLCJzZXNzaW9uX2lkIjoiNzlmZDBlMGItOWE5OS00NzRjLWI0YzQtMGRkMTk5MTlhMDYwIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.-7u2Y_WcJcxM7X8WDQ92repoTgqQ_1OLf5Rkxs9z5Dc"

def make_request(endpoint, method="GET", data=None, description=""):
    """Make API request and return detailed results"""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"📍 {url}")
    if data:
        print(f"📤 {json.dumps(data, indent=2)}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        
        print(f"📊 {response.status_code} {response.reason}")
        
        try:
            result = response.json()
            print(f"📄 Response:")
            print(json.dumps(result, indent=2))
            return result
        except:
            print(f"📄 Raw: {response.text[:500]}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("🔍 EMAIL PREFERENCES vs DIGEST PREVIEW COMPARISON")
    print(f"🕐 Started at: {datetime.now()}")
    print(f"👤 User ID: {USER_ID}")
    
    # Step 1: Update preferences to a specific known state
    print(f"\n{'🔧 STEP 1: SET KNOWN PREFERENCES STATE':=^60}")
    
    test_preferences = {
        "weekly_digest_enabled": True,
        "preferred_day": 5,  # Friday
        "preferred_hour": 15,  # 3 PM
        "timezone": "America/Chicago",
        "no_activity_policy": "suggestions"
    }
    
    update_result = make_request(
        "/api/v1/email/preferences",
        "PUT",
        data=test_preferences,
        description="Update preferences to known test state"
    )
    
    if not update_result or not update_result.get('success'):
        print("❌ Failed to update preferences, stopping test")
        return
    
    # Step 2: Read preferences via email API
    print(f"\n{'📧 STEP 2: READ VIA EMAIL PREFERENCES API':=^60}")
    
    email_api_result = make_request(
        "/api/v1/email/preferences",
        "GET",
        description="Read preferences via EMAIL API (working endpoint)"
    )
    
    # Step 3: Try digest preview and see what it gets
    print(f"\n{'📰 STEP 3: TRY DIGEST PREVIEW':=^60}")
    
    digest_result = make_request(
        "/api/v1/email/digest/preview",
        "POST",
        data={"user_id": USER_ID},
        description="Try digest preview (failing endpoint)"
    )
    
    # Step 4: Analysis
    print(f"\n{'📊 STEP 4: ANALYSIS':=^60}")
    
    if email_api_result and email_api_result.get('success'):
        email_prefs = email_api_result.get('preferences', {})
        print(f"✅ Email API Preferences:")
        print(f"   Weekly Digest: {email_prefs.get('weekly_digest_enabled')}")
        print(f"   Day: {email_prefs.get('preferred_day')}")
        print(f"   Hour: {email_prefs.get('preferred_hour')}")
        print(f"   Timezone: {email_prefs.get('timezone')}")
        print(f"   Policy: {email_prefs.get('no_activity_policy')}")
        
        # Check if they match what we set
        matches = (
            email_prefs.get('weekly_digest_enabled') == test_preferences['weekly_digest_enabled'] and
            email_prefs.get('preferred_day') == test_preferences['preferred_day'] and
            email_prefs.get('preferred_hour') == test_preferences['preferred_hour'] and
            email_prefs.get('timezone') == test_preferences['timezone'] and
            email_prefs.get('no_activity_policy') == test_preferences['no_activity_policy']
        )
        
        if matches:
            print(f"✅ Email API preferences MATCH the updated values")
        else:
            print(f"❌ Email API preferences DO NOT MATCH the updated values")
            print(f"   Expected: {test_preferences}")
            print(f"   Got: {email_prefs}")
    else:
        print(f"❌ Email API failed to return preferences")
    
    if digest_result:
        if digest_result.get('success'):
            print(f"✅ Digest preview succeeded - this would be unexpected!")
            # If it succeeded, check what preferences it used
            payload = digest_result.get('preview', {}).get('payload', {})
            user_data = payload.get('user', {})
            print(f"   User timezone in payload: {user_data.get('timezone')}")
        else:
            print(f"❌ Digest preview failed with: {digest_result.get('message')}")
            print(f"   This suggests the issue is AFTER preferences are retrieved")
            print(f"   The problem is likely in content generation or template rendering")
    else:
        print(f"❌ Digest preview request failed completely")
    
    # Step 5: Reset preferences
    print(f"\n{'🔄 STEP 5: RESET PREFERENCES':=^60}")
    
    reset_preferences = {
        "weekly_digest_enabled": False,
        "preferred_day": 1,
        "preferred_hour": 9,
        "timezone": "America/Los_Angeles",
        "no_activity_policy": "skip"
    }
    
    make_request(
        "/api/v1/email/preferences",
        "PUT",
        data=reset_preferences,
        description="Reset preferences to original state"
    )
    
    print(f"\n{'✅ COMPARISON TEST COMPLETED':=^60}")
    print(f"🕐 Finished at: {datetime.now()}")
    
    print(f"\n📋 Key Findings:")
    print("   - If Email API works but Digest Preview fails:")
    print("     → Database queries are working correctly")
    print("     → Issue is in digest content generation or template rendering")
    print("   - If both fail:")
    print("     → Issue is in the database query layer")
    print("   - If both work:")
    print("     → Issue was resolved by recent changes")

if __name__ == "__main__":
    main()
