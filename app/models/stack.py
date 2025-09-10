from pydantic import BaseModel, Field
from typing import List, Optional, Union
from datetime import datetime
from uuid import UUID

class StackBase(BaseModel):
    """Base stack model with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Stack name")
    description: Optional[str] = Field(None, max_length=1000, description="Stack description")

class StackCreate(StackBase):
    """Model for creating a new stack"""
    pass

class StackUpdate(BaseModel):
    """Model for updating a stack"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)

class StackResponse(StackBase):
    """Model for stack API responses"""
    id: int  # Changed from UUID to int to match existing stacks table
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    items_count: int = 0  # Number of insights in this stack

    class Config:
        from_attributes = True

class StackListResponse(BaseModel):
    """Model for paginated stack list responses"""
    success: bool = True
    data: List[StackResponse]
    total: int
    page: int
    limit: int

class StackDetailResponse(BaseModel):
    """Model for single stack detail responses"""
    success: bool = True
    data: StackResponse
