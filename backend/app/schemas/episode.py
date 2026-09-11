from pydantic import BaseModel

from app.models.enums import PublishStatus


class EpisodeCreate(BaseModel):
    season_id: int
    episode_number: int
    title: str
    synopsis: str | None = None
    duration_seconds: int | None = None
    language: str
    content_group: str | None = None
    status: PublishStatus = PublishStatus.draft


class EpisodeUpdate(BaseModel):
    title: str | None = None
    synopsis: str | None = None
    duration_seconds: int | None = None
    language: str | None = None
    content_group: str | None = None
    status: PublishStatus | None = None


class EpisodeOut(BaseModel):
    id: int
    season_id: int
    episode_number: int
    title: str
    synopsis: str | None
    duration_seconds: int | None
    language: str
    content_group: str | None
    status: PublishStatus

    model_config = {"from_attributes": True}
