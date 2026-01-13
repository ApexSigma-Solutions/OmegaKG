"""Validation API models for OmegaKG.

This module defines Pydantic models for the validation API gateway,
which serves as the single entry point for validated knowledge storage.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DigestType(str, Enum):
    """Types of knowledge digests that can be validated and stored.
    
    NOTE: This enum is extensible - new digest types can be added
    as the system evolves (e.g., github_pr, linear_issue, slack_message).
    """
    CONVERSATION = "conversation"
    TERMINAL_EVENT = "terminal_event"
    LINEAR_ISSUE = "linear_issue"
    GITHUB_PR = "github_pr"


class KnowledgeDigest(BaseModel):
    """Validated knowledge digest for atomic storage.
    
    This model represents a processed, validated piece of knowledge
    ready for storage in Neo4j and pgvector. Workers submit digests
    to the validation API instead of writing directly to databases.
    
    Attributes:
        source_id: Unique identifier from source system (conversation_hash, event_id, etc.)
        digest_type: Type of knowledge (conversation, terminal_event, etc.)
        title: Human-readable title
        content: Main content body
        summary: Optional AI-generated summary
        embedding: Vector embedding (1024 dimensions)
        metadata: Source-specific metadata
        tags: Classification tags
        references: Links to related entities
        captured_at: Original capture timestamp
        processed_at: Worker processing timestamp
    """
    source_id: str = Field(..., description="Unique identifier from source system")
    digest_type: DigestType = Field(..., description="Type of knowledge digest")
    title: str = Field(..., min_length=1, max_length=500, description="Human-readable title")
    content: str = Field(..., min_length=1, description="Main content body")
    summary: Optional[str] = Field(None, description="AI-generated summary")
    embedding: List[float] = Field(..., description="Vector embedding (1024 dimensions)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Source-specific metadata")
    tags: List[str] = Field(default_factory=list, description="Classification tags")
    references: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Links to related entities (files, repos, issues, etc.)"
    )
    captured_at: datetime = Field(..., description="Original capture timestamp")
    processed_at: datetime = Field(default_factory=datetime.utcnow, description="Worker processing timestamp")
    
    @field_validator("embedding")
    @classmethod
    def validate_embedding_dimension(cls, v: List[float]) -> List[float]:
        """Ensure embedding has correct dimensionality."""
        if len(v) != 1024:
            raise ValueError(f"Embedding must have 1024 dimensions, got {len(v)}")
        return v
    
    @field_validator("content")
    @classmethod
    def validate_content_length(cls, v: str) -> str:
        """Ensure content is not empty and within reasonable limits."""
        if not v.strip():
            raise ValueError("Content cannot be empty or whitespace only")
        if len(v) > 1_000_000:  # 1MB limit
            raise ValueError(f"Content too large: {len(v)} bytes > 1MB")
        return v
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Ensure tags are non-empty strings."""
        return [tag.strip() for tag in v if tag and tag.strip()]


class ValidationStatus(str, Enum):
    """Status of validation request."""
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    ERROR = "error"


class ValidationResponse(BaseModel):
    """Response from validation API.
    
    Attributes:
        status: Validation status
        message: Human-readable message
        neo4j_node_id: Neo4j node ID if created
        vector_id: pgvector record ID if created
        source_id: Original source identifier (for deduplication)
        digest_type: Type of digest processed
        created_at: Response timestamp
    """
    status: ValidationStatus = Field(..., description="Validation status")
    message: str = Field(..., description="Human-readable message")
    neo4j_node_id: Optional[str] = Field(None, description="Neo4j node ID if created")
    vector_id: Optional[int] = Field(None, description="pgvector record ID if created")
    source_id: str = Field(..., description="Original source identifier")
    digest_type: DigestType = Field(..., description="Type of digest processed")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "accepted",
                "message": "Knowledge digest validated and stored successfully",
                "neo4j_node_id": "4:abc123:456",
                "vector_id": 12345,
                "source_id": "conv_abc123def456",
                "digest_type": "conversation",
                "created_at": "2026-01-13T15:00:00Z"
            }
        }
