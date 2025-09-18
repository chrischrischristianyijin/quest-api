#!/usr/bin/env python3
"""
Database query debugging script for digest system
Tests specific database queries to identify issues with preferences and profile data
"""
import requests
import json
from datetime import datetime

# Configuration
API_BASE_URL = "https://quest-api-edz1.onrender.com"
USER_ID = "be91dade-1872-444d-b0e7-185ff7e0545a"
AUTH_TOKEN = "eyJhbGciOiJIUzI1NiIsImtpZCI6IjJTWkh3clV5YWRXQm5EaWwiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL3dscGl0c3Rnam9teW56Zm5xa3llLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJiZTkxZGFkZS0xODcyLTQ0NGQtYjBlNy0xODVmZjdlMDU0NWEiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzU4MjY5NjM0LCJpYXQiOjE3NTgxODMyMzQsImVtYWlsIjoic3RhbzA0MjkwNkBnbWFpbC5jb20iLCJwaG9uZSI6IiIsImFwcF9tZXRhZGF0YSI6eyJwcm92aWRlciI6ImVtYWlsIiwicHJvdmlkZXJzIjpbImVtYWlsIl19LCJ1c2VyX21ldGFkYXRhIjp7ImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJuaWNrbmFtZSI6IkdhcnkiLCJ1c2VybmFtZSI6InN0YW8wNDI5MDZfMmI4NzllNzYifSwicm9sZSI6ImF1dGhlbnRpY2F0ZWQiLCJhYWwiOiJhYWwxIiwiYW1yIjpbeyJtZXRob2QiOiJwYXNzd29yZCIsInRpbWVzdGFtcCI6MTc1ODE4MzIzNH1dLCJzZXNzaW9uX2lkIjoiNzlmZDBlMGItOWE5OS00NzRjLWI0YzQtMGRkMTk5MTlhMDYwIiwiaXNfYW5vbnltb3VzIjpmYWxzZX0.-7u2Y_WcJcxM7X8WDQ92repoTgqQ_1OLf5Rkxs9z5Dc"

def test_database_query(endpoint, method="GET", data=None, description=""):
    """Test a specific database query endpoint"""
    print(f"\n{'='*70}")
    print(f"🗄️ {description}")
    print(f"{'='*70}")
    
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"📍 URL: {url}")
    print(f"🔑 Method: {method}")
    if data:
        print(f"📤 Request Body: {json.dumps(data, indent=2)}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=30)
        
        print(f"\n📊 Response Status: {response.status_code} {response.reason}")
        
        try:
            response_json = response.json()
            print(f"\n📄 Response Body (JSON):")
            print(json.dumps(response_json, indent=2))
            
            # Analyze the response structure
            if isinstance(response_json, dict):
                if 'success' in response_json:
                    print(f"\n✅ Success: {response_json['success']}")
                
                if 'data' in response_json:
                    data = response_json['data']
                    if isinstance(data, dict):
                        print(f"\n📋 Data Fields: {list(data.keys())}")
                        # Check for specific fields we expect
                        expected_fields = ['id', 'email', 'nickname', 'username', 'weekly_digest_enabled', 'preferred_day', 'preferred_hour', 'timezone']
                        missing_fields = [field for field in expected_fields if field not in data]
                        if missing_fields:
                            print(f"⚠️ Missing expected fields: {missing_fields}")
                        else:
                            print(f"✅ All expected fields present")
                
                if 'preferences' in response_json:
                    prefs = response_json['preferences']
                    print(f"\n📧 Preferences Fields: {list(prefs.keys())}")
                    print(f"📧 Weekly Digest Enabled: {prefs.get('weekly_digest_enabled')}")
                    print(f"📧 Preferred Day: {prefs.get('preferred_day')}")
                    print(f"📧 Preferred Hour: {prefs.get('preferred_hour')}")
                    print(f"📧 Timezone: {prefs.get('timezone')}")
                    print(f"📧 No Activity Policy: {prefs.get('no_activity_policy')}")
                
                if 'error' in response_json:
                    print(f"❌ Error: {response_json['error']}")
                
        except:
            print(f"\n📄 Response Body (Raw):")
            print(response.text[:1000])
        
        return response
        
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        return None

def test_direct_database_queries():
    """Test direct database queries to understand the data structure"""
    print(f"\n{'🔍 DIRECT DATABASE QUERY ANALYSIS':=^70}")
    
    # Test 1: User Profile Query
    test_database_query(
        "/api/v1/user/profile",
        "GET",
        description="User Profile Query - Check profiles table structure"
    )
    
    # Test 2: Email Preferences Query
    test_database_query(
        "/api/v1/email/preferences",
        "GET",
        description="Email Preferences Query - Check email_preferences table structure"
    )
    
    # Test 3: Update Email Preferences and Verify
    print(f"\n{'🔄 PREFERENCE UPDATE TEST':=^70}")
    
    # First, get current preferences
    current_response = test_database_query(
        "/api/v1/email/preferences",
        "GET",
        description="Current Email Preferences (before update)"
    )
    
    # Update preferences with specific values
    update_data = {
        "weekly_digest_enabled": True,
        "preferred_day": 2,
        "preferred_hour": 14,
        "timezone": "America/New_York",
        "no_activity_policy": "brief"
    }
    
    test_database_query(
        "/api/v1/email/preferences",
        "PUT",
        data=update_data,
        description="Update Email Preferences"
    )
    
    # Verify the update
    test_database_query(
        "/api/v1/email/preferences",
        "GET",
        description="Updated Email Preferences (after update)"
    )
    
    # Test 4: Reset to original values
    reset_data = {
        "weekly_digest_enabled": False,
        "preferred_day": 1,
        "preferred_hour": 9,
        "timezone": "America/Los_Angeles",
        "no_activity_policy": "skip"
    }
    
    test_database_query(
        "/api/v1/email/preferences",
        "PUT",
        data=reset_data,
        description="Reset Email Preferences to Original"
    )
    
    # Final verification
    test_database_query(
        "/api/v1/email/preferences",
        "GET",
        description="Final Email Preferences (after reset)"
    )

def test_digest_preview_with_updated_preferences():
    """Test digest preview with different preference settings"""
    print(f"\n{'📰 DIGEST PREVIEW WITH UPDATED PREFERENCES':=^70}")
    
    # Test with brief policy (should show suggestions even with no activity)
    brief_data = {
        "weekly_digest_enabled": True,
        "preferred_day": 1,
        "preferred_hour": 9,
        "timezone": "America/Los_Angeles",
        "no_activity_policy": "brief"
    }
    
    # Update to brief policy
    test_database_query(
        "/api/v1/email/preferences",
        "PUT",
        data=brief_data,
        description="Set preferences to brief policy"
    )
    
    # Test digest preview
    test_database_query(
        "/api/v1/email/digest/preview",
        "POST",
        data={"user_id": USER_ID},
        description="Digest Preview with Brief Policy"
    )
    
    # Test with suggestions policy
    suggestions_data = {
        "weekly_digest_enabled": True,
        "preferred_day": 1,
        "preferred_hour": 9,
        "timezone": "America/Los_Angeles",
        "no_activity_policy": "suggestions"
    }
    
    # Update to suggestions policy
    test_database_query(
        "/api/v1/email/preferences",
        "PUT",
        data=suggestions_data,
        description="Set preferences to suggestions policy"
    )
    
    # Test digest preview
    test_database_query(
        "/api/v1/email/digest/preview",
        "POST",
        data={"user_id": USER_ID},
        description="Digest Preview with Suggestions Policy"
    )
    
    # Reset to original
    original_data = {
        "weekly_digest_enabled": False,
        "preferred_day": 1,
        "preferred_hour": 9,
        "timezone": "America/Los_Angeles",
        "no_activity_policy": "skip"
    }
    
    test_database_query(
        "/api/v1/email/preferences",
        "PUT",
        data=original_data,
        description="Reset to Original Preferences"
    )

def analyze_supabase_query_patterns():
    """Analyze the Supabase query patterns used in the codebase"""
    print(f"\n{'📊 SUPABASE QUERY PATTERN ANALYSIS':=^70}")
    
    print("""
🔍 Key Findings from Code Analysis:

1. **User Service Pattern:**
   - Uses: self.supabase_service.table('profiles').select('*').eq('id', user_id)
   - Service Role Key: ✅ Has full access
   - Returns: {"success": True, "data": profile_data}

2. **Digest Repo Pattern:**
   - Uses: self.supabase.table("email_preferences").select("*").eq("user_id", user_id)
   - Anon Key: ⚠️ May have limited access
   - Returns: Direct data or None

3. **Potential Issues:**
   - Different Supabase client instances (anon vs service role)
   - Different response handling patterns
   - Row Level Security (RLS) policies might block anon key
   - Table permissions might be different

4. **Expected vs Actual:**
   - Expected: Real user data from database
   - Actual: May be getting default/fallback values
   - Issue: Database queries might be failing silently

🔧 Recommended Fixes:
   - Use service role key for all digest queries
   - Add proper error handling and logging
   - Verify RLS policies for email_preferences table
   - Check table permissions for anon vs service role
""")

def main():
    print("🗄️ DATABASE QUERY DEBUGGING FOR DIGEST SYSTEM")
    print(f"🕐 Test started at: {datetime.now()}")
    print(f"🌐 Base URL: {API_BASE_URL}")
    print(f"👤 User ID: {USER_ID}")
    
    # Test direct database queries
    test_direct_database_queries()
    
    # Test digest preview with different preferences
    test_digest_preview_with_updated_preferences()
    
    # Analyze query patterns
    analyze_supabase_query_patterns()
    
    print(f"\n{'✅ DATABASE QUERY DEBUGGING COMPLETED':=^70}")
    print(f"🕐 Test finished at: {datetime.now()}")
    print("\n📋 Key Things to Check:")
    print("   - Are preferences being saved correctly?")
    print("   - Are preferences being retrieved correctly?")
    print("   - Do different policies affect digest preview?")
    print("   - Are there any database permission issues?")
    print("   - Is the digest preview working with different policies?")

if __name__ == "__main__":
    main()
