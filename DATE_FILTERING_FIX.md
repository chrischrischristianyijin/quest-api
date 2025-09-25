# Date Filtering Fix - Why AI Summary Works But Tags Don't

## Issue Identified
AI summary was working correctly, but insights with tags were not showing in the weekly digest emails.

## Root Cause Analysis

### Different Data Retrieval Methods:

1. **AI Summary Service** (`ai_summary_service.py`):
   - ✅ Uses `generate_weekly_insights_summary(user_id)` 
   - ✅ Calls `_get_weekly_insights(user_id)` internally
   - ✅ Gets ALL insights first, then filters in Python
   - ✅ **Uses inclusive date filtering**: `>= start_utc` (no end_utc check)

2. **Tags Section** (`digest_repo.py`):
   - ❌ Uses `get_user_activity(user_id, start_utc, end_utc)`
   - ❌ Gets ALL insights first, then filters in Python (after our fix)
   - ❌ **Used restrictive date filtering**: `start_utc <= date < end_utc`

## The Critical Difference

### AI Summary Service Date Logic (Working):
```python
# More inclusive - only checks >= start_utc
if c and c >= start_utc:
    in_window = True
elif u and u >= start_utc:
    in_window = True
```

### Digest Repo Date Logic (Not Working):
```python
# More restrictive - checks strict range
if created_dt and start_utc <= created_dt < end_utc:
    insights.append(insight)
elif updated_dt and start_utc <= updated_dt < end_utc:
    insights.append(insight)
```

## Fix Applied

### Updated `/app/services/digest_repo.py`

**Changed date filtering logic to match AI summary service:**

#### Before (Restrictive):
```python
# Include if created OR updated within the time window
if created_dt and start_utc <= created_dt < end_utc:
    insights.append(insight)
elif updated_dt and start_utc <= updated_dt < end_utc:
    insights.append(insight)
```

#### After (Inclusive - Same as AI Summary):
```python
# Use the same logic as AI summary service: >= start_utc (more inclusive)
in_window = False
if created_dt and created_dt >= start_utc:
    in_window = True
elif updated_dt and updated_dt >= start_utc:
    in_window = True

if in_window:
    insights.append(insight)
```

## Why This Fixes the Issue

1. **Consistent Data**: Both AI summary and tags sections now use the same date filtering logic
2. **More Inclusive**: The `>= start_utc` logic includes more insights than the strict range
3. **Matches Working Pattern**: Uses the exact same logic that makes AI summary work
4. **Applied to Both**: Updated both insights and stacks filtering consistently

## Expected Result

After this fix:
- ✅ **AI Summary**: Continues to work (already working)
- ✅ **Insights with Tags**: Should now show in "本周收藏" section
- ✅ **Consistent Data**: Both sections use the same insights data
- ✅ **Enhanced Debugging**: Logs will show the filtered insights count

## Files Modified

1. **`/app/services/digest_repo.py`** - Updated `get_user_activity()` method
   - Changed date filtering logic from restrictive to inclusive
   - Applied same logic to both insights and stacks
   - Now matches the working AI summary service pattern

## Testing

To test the fix:
1. Deploy the updated code
2. Trigger a digest email
3. Check logs for:
   - "DIGEST REPO: Filtered to X insights in date range"
   - "Found X tagged insights out of Y total"
   - "Tags section data: [...]"

The insights with tags should now appear in the weekly digest email, matching the same data that generates the AI summary.
