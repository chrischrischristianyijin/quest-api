#!/usr/bin/env python3
"""
Test script to check Supabase email_preferences table
"""
import os
from supabase import create_client, Client

def test_supabase_table():
    """Test the email_preferences table structure and permissions"""
    
    # Initialize Supabase client
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Missing SUPABASE_URL or SUPABASE_ANON_KEY environment variables")
        return
    
    print(f"✅ Supabase URL: {supabase_url}")
    print(f"✅ Supabase Key length: {len(supabase_key)}")
    
    try:
        supabase: Client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client created successfully")
        
        # Test 1: Try to select from the table to check if it exists
        print("\n=== Test 1: Check table existence ===")
        try:
            response = supabase.table("email_preferences").select("*").limit(1).execute()
            print(f"✅ Table exists. Response: {response}")
            print(f"Data count: {len(response.data) if response.data else 0}")
            if response.data:
                print(f"Sample record: {response.data[0]}")
        except Exception as e:
            print(f"❌ Error accessing table: {e}")
            return
        
        # Test 2: Try to insert a test record
        print("\n=== Test 2: Try inserting test record ===")
        test_user_id = "test-user-12345"
        test_preferences = {
            "user_id": test_user_id,
            "weekly_digest_enabled": True,
            "preferred_day": 1,
            "preferred_hour": 9,
            "timezone": "UTC",
            "no_activity_policy": "brief"
        }
        
        try:
            # First, try to delete any existing test record
            supabase.table("email_preferences").delete().eq("user_id", test_user_id).execute()
            
            # Now try to insert
            response = supabase.table("email_preferences").insert(test_preferences).execute()
            print(f"✅ Insert successful. Response: {response}")
            print(f"Inserted data: {response.data}")
            
            # Clean up - delete the test record
            cleanup_response = supabase.table("email_preferences").delete().eq("user_id", test_user_id).execute()
            print(f"✅ Cleanup successful. Deleted: {cleanup_response.data}")
            
        except Exception as e:
            print(f"❌ Error inserting test record: {e}")
            print(f"Error type: {type(e)}")
            
            # Try to get more details about the error
            if hasattr(e, 'details'):
                print(f"Error details: {e.details}")
            if hasattr(e, 'message'):
                print(f"Error message: {e.message}")
        
        # Test 3: Check what columns exist in the table
        print("\n=== Test 3: Check table schema ===")
        try:
            # Try to get all records to see the structure
            response = supabase.table("email_preferences").select("*").execute()
            if response.data:
                print("Table columns found:")
                for key in response.data[0].keys():
                    print(f"  - {key}")
            else:
                print("No records in table to examine structure")
                
        except Exception as e:
            print(f"❌ Error checking table schema: {e}")
        
    except Exception as e:
        print(f"❌ Error creating Supabase client: {e}")

if __name__ == "__main__":
    print("=== Supabase Email Preferences Table Test ===\n")
    test_supabase_table()
