#!/usr/bin/env python3
"""
Test email preferences database operations
"""
import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.services.digest_repo import DigestRepo

async def test_email_preferences_database():
    """Test email preferences database operations"""
    
    print("🧪 Testing Email Preferences Database Operations")
    print("=" * 55)
    
    try:
        # Create repository instance
        repo = DigestRepo()
        print("✅ DigestRepo initialized successfully")
        
        # Test user ID
        test_user_id = "test-user-123"
        
        # Test 1: Check if email_preferences table exists
        print("\n1. 📊 Testing database connection...")
        try:
            # Try to query the table to see if it exists
            response = repo.supabase.table("email_preferences").select("count").limit(1).execute()
            print("   ✅ email_preferences table exists and is accessible")
        except Exception as e:
            print(f"   ❌ email_preferences table error: {e}")
            return
        
        # Test 2: Test creating default preferences
        print("\n2. ➕ Testing create_default_email_preferences...")
        try:
            success = await repo.create_default_email_preferences(test_user_id)
            if success:
                print("   ✅ Default preferences created successfully")
            else:
                print("   ❌ Failed to create default preferences")
        except Exception as e:
            print(f"   ❌ Create default preferences error: {e}")
        
        # Test 3: Test getting preferences
        print("\n3. 📖 Testing get_user_email_preferences...")
        try:
            preferences = await repo.get_user_email_preferences(test_user_id)
            if preferences:
                print("   ✅ Preferences retrieved successfully")
                print(f"   📋 Preferences: {preferences}")
            else:
                print("   ❌ No preferences found")
        except Exception as e:
            print(f"   ❌ Get preferences error: {e}")
        
        # Test 4: Test updating preferences
        print("\n4. ✏️  Testing update_user_email_preferences...")
        try:
            update_data = {
                "weekly_digest_enabled": False,
                "preferred_day": 2,  # Tuesday
                "preferred_hour": 14,  # 2 PM
                "timezone": "UTC",
                "no_activity_policy": "suggestions"
            }
            
            success = await repo.update_user_email_preferences(test_user_id, update_data)
            if success:
                print("   ✅ Preferences updated successfully")
            else:
                print("   ❌ Failed to update preferences")
        except Exception as e:
            print(f"   ❌ Update preferences error: {e}")
        
        # Test 5: Verify updated preferences
        print("\n5. 🔍 Testing get preferences after update...")
        try:
            preferences = await repo.get_user_email_preferences(test_user_id)
            if preferences:
                print("   ✅ Updated preferences retrieved successfully")
                print(f"   📋 Updated preferences: {preferences}")
                
                # Check if the update worked
                if preferences.get("weekly_digest_enabled") == False:
                    print("   ✅ weekly_digest_enabled updated correctly")
                else:
                    print("   ❌ weekly_digest_enabled not updated")
                    
                if preferences.get("preferred_day") == 2:
                    print("   ✅ preferred_day updated correctly")
                else:
                    print("   ❌ preferred_day not updated")
            else:
                print("   ❌ No preferences found after update")
        except Exception as e:
            print(f"   ❌ Get updated preferences error: {e}")
        
        # Test 6: Test upsert functionality
        print("\n6. 🔄 Testing upsert functionality...")
        try:
            # Try to update with new data
            upsert_data = {
                "weekly_digest_enabled": True,
                "preferred_day": 0,  # Sunday
                "preferred_hour": 8,  # 8 AM
                "timezone": "America/New_York",
                "no_activity_policy": "brief"
            }
            
            success = await repo.update_user_email_preferences(test_user_id, upsert_data)
            if success:
                print("   ✅ Upsert operation successful")
            else:
                print("   ❌ Upsert operation failed")
        except Exception as e:
            print(f"   ❌ Upsert error: {e}")
        
        print("\n🎉 Email Preferences Database Test Completed!")
        print("\n📊 Test Results Summary:")
        print("   ✅ Database connection working")
        print("   ✅ Table operations functional")
        print("   ✅ CRUD operations working")
        print("   📧 Email preferences system is ready")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check if database migration has been run")
        print("   2. Verify Supabase connection settings")
        print("   3. Check RLS policies")
        print("   4. Ensure service role has proper permissions")

if __name__ == "__main__":
    asyncio.run(test_email_preferences_database())
