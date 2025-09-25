#!/usr/bin/env python3
"""
Debug script to check email users in the database
"""
import os
import asyncio
from datetime import datetime, timezone
from supabase import create_client

# Load environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") 
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not all([SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY]):
    print("❌ Missing environment variables")
    exit(1)

# Create clients
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
supabase_service = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

async def debug_email_users():
    print("🔍 Debugging Email Users in Database...")
    
    # Step 1: Check email_preferences table
    print("\n1️⃣ Checking email_preferences table...")
    try:
        prefs_response = supabase.table("email_preferences").select("*").execute()
        print(f"📊 Total email preferences records: {len(prefs_response.data)}")
        
        if prefs_response.data:
            print("📋 Sample preferences:")
            for i, pref in enumerate(prefs_response.data[:3]):
                print(f"   {i+1}. User: {pref.get('user_id')}, Enabled: {pref.get('weekly_digest_enabled')}")
        
        # Check how many have weekly_digest_enabled=True
        enabled_count = len([p for p in prefs_response.data if p.get('weekly_digest_enabled')])
        print(f"✅ Users with weekly_digest_enabled=True: {enabled_count}")
        
    except Exception as e:
        print(f"❌ Error checking email_preferences: {e}")
    
    # Step 2: Check auth.users table
    print("\n2️⃣ Checking auth.users table...")
    try:
        # This might not work with anon key, try service key
        auth_response = supabase_service.table("auth.users").select("id, email").limit(5).execute()
        print(f"📊 Total auth.users records (sample): {len(auth_response.data)}")
        
        if auth_response.data:
            print("📋 Sample auth.users:")
            for i, user in enumerate(auth_response.data[:3]):
                print(f"   {i+1}. ID: {user.get('id')}, Email: {user.get('email')}")
                
    except Exception as e:
        print(f"❌ Error checking auth.users: {e}")
    
    # Step 3: Check profiles table
    print("\n3️⃣ Checking profiles table...")
    try:
        profiles_response = supabase_service.table("profiles").select("id, nickname, username").limit(5).execute()
        print(f"📊 Total profiles records (sample): {len(profiles_response.data)}")
        
        if profiles_response.data:
            print("📋 Sample profiles:")
            for i, profile in enumerate(profiles_response.data[:3]):
                print(f"   {i+1}. ID: {profile.get('id')}, Nickname: {profile.get('nickname')}, Username: {profile.get('username')}")
                
    except Exception as e:
        print(f"❌ Error checking profiles: {e}")
    
    # Step 4: Test the actual query logic
    print("\n4️⃣ Testing the actual query logic...")
    try:
        # Get users with weekly_digest_enabled=True
        prefs_response = supabase.table("email_preferences").select(
            "user_id, weekly_digest_enabled, preferred_day, preferred_hour, timezone, no_activity_policy"
        ).eq("weekly_digest_enabled", True).execute()
        
        print(f"📊 Found {len(prefs_response.data)} users with weekly_digest_enabled=True")
        
        if prefs_response.data:
            print("📋 Users with enabled digest:")
            for i, pref in enumerate(prefs_response.data):
                user_id = pref["user_id"]
                print(f"   {i+1}. User ID: {user_id}")
                
                # Try to get email for this user
                try:
                    auth_response = supabase_service.table("auth.users").select("email").eq("id", user_id).execute()
                    if auth_response.data:
                        email = auth_response.data[0]["email"]
                        print(f"      ✅ Email: {email}")
                    else:
                        print(f"      ❌ No email found in auth.users")
                except Exception as e:
                    print(f"      ❌ Error getting email: {e}")
                
                # Try to get profile for this user
                try:
                    profile_response = supabase_service.table("profiles").select("nickname, username").eq("id", user_id).execute()
                    if profile_response.data:
                        profile = profile_response.data[0]
                        print(f"      ✅ Profile: {profile.get('nickname')} / {profile.get('username')}")
                    else:
                        print(f"      ❌ No profile found")
                except Exception as e:
                    print(f"      ❌ Error getting profile: {e}")
                
                print()  # Empty line for readability
        else:
            print("❌ No users found with weekly_digest_enabled=True")
            
    except Exception as e:
        print(f"❌ Error in query logic test: {e}")

if __name__ == "__main__":
    asyncio.run(debug_email_users())
