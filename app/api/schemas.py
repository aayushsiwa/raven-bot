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
    cursor: Optional[int] = Field(default=None, ge=0)
    from_ts: Optional[int] = Field(default=None, ge=0)
    to_ts: Optional[int] = Field(default=None, ge=0)


class SignupPayload(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)


class LoginPayload(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenPayload(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class OAuthLoginPayload(BaseModel):
    provider: str = Field(..., min_length=3, max_length=32)
    provider_user_id: str = Field(..., min_length=1, max_length=128)
    username: str = Field(..., min_length=3, max_length=32)
    email: Optional[str] = Field(default=None, max_length=255)
    display_name: Optional[str] = Field(default=None, max_length=255)
    avatar_url: Optional[str] = Field(default=None, max_length=1000)


class FeedPreferenceChoice(BaseModel):
    provider: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    topic: str = Field(..., min_length=1)


class FeedPreferencesPayload(BaseModel):
    choices: list[FeedPreferenceChoice] = Field(default_factory=list)


class CustomFeedPayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=10, max_length=2048)
    category: str = Field(default="custom", min_length=1, max_length=64)
    topic: str = Field(default="user", min_length=1, max_length=64)


class CustomFeedUpdatePayload(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = Field(default=None)


class LinkProviderPayload(BaseModel):
    provider: str = Field(..., min_length=3, max_length=32)
    state: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)


class SaveArticlePayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    url: str = Field(..., min_length=10, max_length=2048)
    summary: Optional[str] = Field(default=None, max_length=2000)
    source: Optional[str] = Field(default=None, max_length=255)
