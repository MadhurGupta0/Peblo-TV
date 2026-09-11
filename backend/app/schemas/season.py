from pydantic import BaseModel


class SeasonCreate(BaseModel):
    season_number: int
    title: str | None = None


class SeasonUpdate(BaseModel):
    title: str | None = None


class SeasonOut(BaseModel):
    id: int
    show_id: int
    season_number: int
    title: str | None

    model_config = {"from_attributes": True}
