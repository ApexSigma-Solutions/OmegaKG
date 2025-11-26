"""
Linear Domain Models

Pydantic v2 models representing Linear webhook payloads and entities.
These are pure domain models, independent of database schemas.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime


class LinearWebhookPayload(BaseModel):
    """
    Root webhook payload structure from Linear.
    """
    action: str
    type: str
    data: dict[str, Any]
    createdAt: Optional[datetime] = None
    
    model_config = {"extra": "allow"}


class LinearUser(BaseModel):
    """
    Linear user representation.
    """
    id: str
    name: Optional[str] = None
    email: Optional[str] = None
    active: bool = True
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    
    model_config = {"extra": "allow"}


class LinearLabel(BaseModel):
    """
    Linear label/tag representation.
    """
    id: str
    name: str
    color: Optional[str] = None
    
    model_config = {"extra": "allow"}


class LinearState(BaseModel):
    """
    Linear workflow state (e.g., Todo, In Progress, Done).
    """
    id: str
    name: str
    color: Optional[str] = None
    type: str  # "started", "completed", "canceled", "triage", "backlog"
    
    model_config = {"extra": "allow"}


class LinearIssue(BaseModel):
    """
    Linear Issue representation.
    
    This is the primary entity we map to Obsidian markdown files.
    """
    id: str
    identifier: str  # e.g., "APX-123"
    title: str
    description: Optional[str] = None
    state: Optional[LinearState] = None
    priority: Optional[int] = None
    labels: List[LinearLabel] = Field(default_factory=list)
    assignee: Optional[LinearUser] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    url: Optional[str] = None
    
    model_config = {"extra": "allow"}
    
    @field_validator('priority')
    @classmethod
    def normalize_priority(cls, v: Optional[int]) -> int:
        """
        Normalize Linear priority to 0-4 range.
        
        Linear priority scale:
        - 0: None
        - 1: Urgent
        - 2: High
        - 3: Medium
        - 4: Low
        
        Args:
            v: Raw priority value
            
        Returns:
            Normalized priority (0-4)
        """
        if v is None:
            return 0
        return max(0, min(4, v))


class LinearComment(BaseModel):
    """
    Linear comment/activity representation.
    """
    id: str
    body: str
    issue_id: str = Field(alias="issueId")
    user: Optional[LinearUser] = None
    createdAt: Optional[datetime] = None
    
    model_config = {"extra": "allow", "populate_by_name": True}
