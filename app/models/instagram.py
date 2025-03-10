from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class InstagramPost(BaseModel):
    """Model for an Instagram post."""

    post_id: str = Field(..., description="The ID of the post")
    shortcode: str = Field(..., description="The shortcode of the post")
    url: HttpUrl = Field(..., description="The URL of the post")
    caption: str = Field(default="", description="The caption of the post")
    likes_count: int = Field(default=0, description="The number of likes on the post")
    comments_count: int = Field(
        default=0, description="The number of comments on the post"
    )
    timestamp: datetime | None = Field(None, description="The timestamp of the post")
    image_url: HttpUrl | None = Field(None, description="The URL of the post image")
    hashtags: list[str] = Field(
        default_factory=list, description="The hashtags used in the post"
    )
    contains_target_hashtag: bool = Field(
        default=False,
        description="Whether the post contains the target hashtag",
    )


class InstagramPostsResponse(BaseModel):
    """Response model for Instagram posts."""

    account: str = Field(..., description="The Instagram account")
    posts: list[InstagramPost] = Field(..., description="The list of Instagram posts")
    posts_count: int = Field(..., description="The number of Instagram posts")
    filtered_count: int = Field(
        ..., description="The number of Instagram posts with target hashtag"
    )
    target_hashtag: str = Field(..., description="The target hashtag for filtering")
