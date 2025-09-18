#!/usr/bin/env python3
"""
Script to add enhanced debug logging to digest preview endpoint
This will help identify exactly where the error occurs
"""

def add_debug_logging_to_digest_preview():
    """Add debug logging to the digest preview endpoint"""
    
    # Read the current email.py file
    try:
        with open("app/api/v1/email.py", "r") as f:
            content = f.read()
    except FileNotFoundError:
        print("❌ app/api/v1/email.py not found")
        return False
    
    # Check if debug logging is already added
    if "DEBUG LOGGING ADDED" in content:
        print("✅ Debug logging already added to digest preview endpoint")
        return True
    
    # Find the digest preview function and add debug logging
    debug_logging_code = '''
    # DEBUG LOGGING ADDED - Remove this after debugging
    import traceback
    logger.info(f"🔍 DEBUG: Starting digest preview for user {user_id}")
    
    try:
        logger.info(f"🔍 DEBUG: Getting user email preferences...")
        user_prefs = await repo.get_user_email_preferences(user_id)
        logger.info(f"🔍 DEBUG: User preferences result: {user_prefs}")
        
        if not user_prefs:
            logger.error(f"🔍 DEBUG: No user preferences found for user {user_id}")
            raise HTTPException(status_code=404, detail="User preferences not found")
        
        logger.info(f"🔍 DEBUG: Getting user profile data...")
        user_profile = await repo.get_user_profile_data(user_id)
        logger.info(f"🔍 DEBUG: User profile result: {user_profile}")
        
        if not user_profile:
            logger.error(f"🔍 DEBUG: No user profile found for user {user_id}")
            raise HTTPException(status_code=404, detail="User profile not found")
        
        logger.info(f"🔍 DEBUG: Building user data object...")
        user_data = {
            "id": user_profile["id"],
            "email": user_profile["email"],
            "first_name": user_profile["first_name"],
            "nickname": user_profile.get("nickname"),
            "username": user_profile.get("username"),
            "avatar_url": user_profile.get("avatar_url"),
            "timezone": user_prefs["timezone"]
        }
        logger.info(f"🔍 DEBUG: User data built: {user_data}")
        
        logger.info(f"🔍 DEBUG: Determining week boundaries...")
        if request.week_start:
            week_start = datetime.fromisoformat(request.week_start).date()
            logger.info(f"🔍 DEBUG: Using provided week_start: {week_start}")
        else:
            now_utc = datetime.now(timezone.utc)
            logger.info(f"🔍 DEBUG: Current UTC time: {now_utc}")
            week_boundaries = get_week_boundaries(now_utc, user_prefs["timezone"])
            logger.info(f"🔍 DEBUG: Week boundaries: {week_boundaries}")
            week_start = week_boundaries["prev_week_start"].date()
            logger.info(f"🔍 DEBUG: Calculated week_start: {week_start}")
        
        logger.info(f"🔍 DEBUG: Getting user activity...")
        start_utc = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_utc = start_utc.replace(hour=23, minute=59, second=59) + timedelta(days=6)
        logger.info(f"🔍 DEBUG: Activity time range: {start_utc} to {end_utc}")
        
        insights, stacks = await repo.get_user_activity(user_id, start_utc, end_utc)
        logger.info(f"🔍 DEBUG: Found {len(insights)} insights and {len(stacks)} stacks")
        logger.info(f"🔍 DEBUG: Sample insights: {insights[:2] if insights else 'None'}")
        logger.info(f"🔍 DEBUG: Sample stacks: {stacks[:2] if stacks else 'None'}")
        
        logger.info(f"🔍 DEBUG: Generating content...")
        content_generator = DigestContentGenerator()
        logger.info(f"🔍 DEBUG: Content generator created")
        
        payload = content_generator.build_user_digest_payload(
            user_data, insights, stacks, user_prefs["no_activity_policy"]
        )
        logger.info(f"🔍 DEBUG: Payload generated successfully")
        logger.info(f"🔍 DEBUG: Payload keys: {list(payload.keys()) if payload else 'None'}")
        
        logger.info(f"🔍 DEBUG: Rendering email content...")
        from ...services.digest_job import DigestJob
        job = DigestJob(repo)
        logger.info(f"🔍 DEBUG: DigestJob created")
        
        render_result = await job._render_email_content(payload)
        logger.info(f"🔍 DEBUG: Render result: {render_result}")
        
        if not render_result["success"]:
            logger.error(f"🔍 DEBUG: Email rendering failed: {render_result}")
            raise HTTPException(status_code=500, detail="Failed to render email content")
        
        logger.info(f"🔍 DEBUG: Digest preview generated successfully!")
        return {
            "success": True,
            "preview": {
                "subject": render_result["subject"],
                "html_content": render_result["html_content"],
                "text_content": render_result["text_content"],
                "payload": payload
            }
        }
        
    except HTTPException as he:
        logger.error(f"🔍 DEBUG: HTTPException in digest preview: {he}")
        raise he
    except Exception as e:
        logger.error(f"🔍 DEBUG: Unexpected error in digest preview: {e}")
        logger.error(f"🔍 DEBUG: Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to generate preview: {str(e)}")
    # END DEBUG LOGGING'''
    
    # Find the preview_digest function and replace its content
    import re
    
    # Pattern to match the entire function
    pattern = r'(@router\.post\("/digest/preview"\)\s*async def preview_digest\([^)]+\):[^}]+?except Exception as e:[^}]+?raise HTTPException[^}]+?)\n'
    
    if re.search(pattern, content, re.DOTALL):
        print("✅ Found digest preview function, adding debug logging...")
        
        # Replace the try-except block with our debug version
        new_content = re.sub(
            r'("""Preview the next digest for a user\."""\s*try:)(.*?)(except Exception as e:.*?raise HTTPException.*?)\n',
            f'"""Preview the next digest for a user."""{debug_logging_code}\n',
            content,
            flags=re.DOTALL
        )
        
        # Write the modified content back
        try:
            with open("app/api/v1/email.py", "w") as f:
                f.write(new_content)
            print("✅ Debug logging added successfully!")
            print("🔍 Now run your local server and the digest preview will show detailed error messages")
            return True
        except Exception as e:
            print(f"❌ Failed to write debug logging: {e}")
            return False
    else:
        print("❌ Could not find digest preview function to modify")
        return False

def main():
    print("🔧 ADDING DEBUG LOGGING TO DIGEST PREVIEW")
    print("=" * 50)
    
    success = add_debug_logging_to_digest_preview()
    
    if success:
        print("\n✅ Debug logging added successfully!")
        print("\n📋 Next steps:")
        print("1. Run: python3 run_local_debug_server.py")
        print("2. In another terminal, run: python3 test_local_server_debug.py")
        print("3. Watch the server console for detailed error messages")
        print("\n⚠️ Remember to remove debug logging after debugging!")
    else:
        print("\n❌ Failed to add debug logging")
        print("💡 You may need to add it manually to the digest preview function")

if __name__ == "__main__":
    main()
