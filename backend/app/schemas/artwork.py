from pydantic import BaseModel


class ArtworkOut(BaseModel):
    id: int
    owner_type: str
    owner_id: int
    kind: str
    url: str
    width: int
    height: int
    bytes: int
    content_type: str
    checksum: str

    model_config = {"from_attributes": True}


class FieldError(BaseModel):
    field: str
    code: str
    message: str


class ValidationErrorResponse(BaseModel):
    errors: list[FieldError]
