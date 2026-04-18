from typing import Optional

from pydantic import BaseModel, Field


class SubscriptionPayload(BaseModel):
    channel_id: int = Field(..., gt=0)
    guild_id: Optional[int] = None
    provider: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)


class SubscriptionDeletePayload(BaseModel):
    channel_id: int = Field(..., gt=0)
    provider: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)


class FeedBatchRequest(BaseModel):
    provider: str
    category: str
    topic: str


class BatchRssPayload(BaseModel):
    feeds: list[FeedBatchRequest]
    limit: int = Field(5, ge=1, le=30)
