from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from uuid import UUID
import logging

from app.core.database import get_supabase
from app.models.stack import (
    StackCreate, 
    StackUpdate, 
    StackResponse, 
    StackListResponse,
    StackDetailResponse
)
from app.services.auth_service import AuthService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

@router.post("/", response_model=StackDetailResponse)
async def create_stack(
    stack_data: StackCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Create a new stack"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        supabase = get_supabase()
        
        # Insert new stack
        result = supabase.table('stacks').insert({
            'user_id': current_user['id'],
            'name': stack_data.name,
            'description': stack_data.description
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=400, detail="Failed to create stack")
        
        stack = result.data[0]
        logger.info(f"✅ Created stack {stack['id']} for user {current_user['id']}")
        
        return StackDetailResponse(
            success=True,
            data=StackResponse(
                id=stack['id'],
                user_id=stack['user_id'],
                name=stack['name'],
                description=stack['description'],
                created_at=stack['created_at'],
                updated_at=stack['updated_at']
            )
        )
        
    except Exception as e:
        logger.error(f"❌ Error creating stack: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create stack: {str(e)}")

@router.get("/", response_model=StackListResponse)
async def get_stacks(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    include_insights: bool = Query(False, description="Include insights in response"),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get user's stacks with optional insights"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        supabase = get_supabase()
        
        # Calculate offset
        offset = (page - 1) * limit
        
        if include_insights:
            # Get stacks with their insights
            result = supabase.table('stacks').select("""
                *,
                insights!stack_id(
                    id,
                    title,
                    description,
                    url,
                    image_url,
                    created_at,
                    updated_at,
                    tags
                )
            """).eq('user_id', current_user['id']).order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        else:
            # Get stacks only
            result = supabase.table('stacks').select("*").eq('user_id', current_user['id']).order('created_at', desc=True).range(offset, offset + limit - 1).execute()
        
        # Get total count
        count_result = supabase.table('stacks').select('id', count='exact').eq('user_id', current_user['id']).execute()
        total = count_result.count or 0
        
        stacks = []
        for stack in result.data:
            # Count insights for this stack
            insights_count = 0
            if include_insights and 'insights' in stack:
                insights_count = len(stack['insights'])
            else:
                # Count insights separately if not included
                count_result = supabase.table('insights').select('id', count='exact').eq('stack_id', stack['id']).execute()
                insights_count = count_result.count or 0
            
            stacks.append(StackResponse(
                id=stack['id'],
                user_id=stack['user_id'],
                name=stack['name'],
                description=stack['description'],
                created_at=stack['created_at'],
                updated_at=stack['updated_at'],
                items_count=insights_count
            ))
        
        logger.info(f"✅ Retrieved {len(stacks)} stacks for user {current_user['id']}")
        
        return StackListResponse(
            success=True,
            data=stacks,
            total=total,
            page=page,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"❌ Error getting stacks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stacks: {str(e)}")

@router.get("/{stack_id}", response_model=StackDetailResponse)
async def get_stack(
    stack_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get a specific stack by ID with its insights"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        supabase = get_supabase()
        
        # Get stack with insights
        result = supabase.table('stacks').select("""
            *,
            insights!stack_id(
                id,
                title,
                description,
                url,
                image_url,
                created_at,
                updated_at,
                tags
            )
        """).eq('id', stack_id).eq('user_id', current_user['id']).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Stack not found")
        
        stack = result.data[0]
        insights_count = len(stack.get('insights', []))
        
        logger.info(f"✅ Retrieved stack {stack_id} with {insights_count} insights for user {current_user['id']}")
        
        return StackDetailResponse(
            success=True,
            data=StackResponse(
                id=stack['id'],
                user_id=stack['user_id'],
                name=stack['name'],
                description=stack['description'],
                created_at=stack['created_at'],
                updated_at=stack['updated_at'],
                items_count=insights_count
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting stack {stack_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get stack: {str(e)}")

@router.put("/{stack_id}", response_model=StackDetailResponse)
async def update_stack(
    stack_id: int,
    stack_data: StackUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update a stack"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        supabase = get_supabase()
        
        # Prepare update data
        update_data = {}
        if stack_data.name is not None:
            update_data['name'] = stack_data.name
        if stack_data.description is not None:
            update_data['description'] = stack_data.description
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Update stack
        result = supabase.table('stacks').update(update_data).eq('id', stack_id).eq('user_id', current_user['id']).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Stack not found")
        
        stack = result.data[0]
        logger.info(f"✅ Updated stack {stack_id} for user {current_user['id']}")
        
        return StackDetailResponse(
            success=True,
            data=StackResponse(
                id=stack['id'],
                user_id=stack['user_id'],
                name=stack['name'],
                description=stack['description'],
                created_at=stack['created_at'],
                updated_at=stack['updated_at']
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating stack {stack_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update stack: {str(e)}")

@router.delete("/{stack_id}")
async def delete_stack(
    stack_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Delete a stack and remove stack_id from all its insights"""
    try:
        auth_service = AuthService()
        current_user = await auth_service.get_current_user(credentials.credentials)
        
        supabase = get_supabase()
        
        # First, remove stack_id from all insights in this stack
        insights_result = supabase.table('insights').update({'stack_id': None}).eq('stack_id', stack_id).eq('user_id', current_user['id']).execute()
        
        # Then delete the stack
        result = supabase.table('stacks').delete().eq('id', stack_id).eq('user_id', current_user['id']).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Stack not found")
        
        logger.info(f"✅ Deleted stack {stack_id} and removed stack_id from {len(insights_result.data)} insights for user {current_user['id']}")
        
        return {"success": True, "message": "Stack deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting stack {stack_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete stack: {str(e)}")