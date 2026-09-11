from pydantic import BaseModel

from app.models.enums import PublishStatus


class ShowCreate(BaseModel):
    slug: str
    title: str
    synopsis: str | None = None
    section: str | None = None
    categories: list[str] = []
    status: PublishStatus = PublishStatus.draft


class ShowUpdate(BaseModel):
    title: str | None = None
    synopsis: str | None = None
    section: str | None = None
    categories: list[str] | None = None
    status: PublishStatus | None = None


class ShowOut(BaseModel):
    id: int
    slug: str
    title: str
    synopsis: str | None
    section: str | None
    categories: list[str]
    status: PublishStatus

    model_config = {"from_attributes": True}
