import hashlib

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.artwork_specs import ARTWORK_SPECS
from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppValidationError
from app.models.artwork import Artwork
from app.models.enums import ArtworkKind, ArtworkOwnerType, UserRole
from app.models.episode import Episode
from app.models.show import Show
from app.models.user import User
from app.schemas.artwork import ArtworkOut, ValidationErrorResponse
from app.services.artwork_validation import ArtworkValidationError, validate_artwork
from app.storage import get_storage

router = APIRouter(prefix="/admin", tags=["artwork"])


def _owner_exists(db: Session, owner_type: str, owner_id: int) -> bool:
    model = Show if owner_type == ArtworkOwnerType.show.value else Episode
    return db.execute(select(model.id).where(model.id == owner_id)).scalar_one_or_none() is not None


@router.get("/artwork", response_model=list[ArtworkOut])
def list_artwork(
    owner_type: str = Query(...),
    owner_id: int = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_role(UserRole.editor, UserRole.admin)),
) -> list[ArtworkOut]:
    if owner_type not in (ArtworkOwnerType.show.value, ArtworkOwnerType.episode.value):
        raise AppValidationError.single("owner_type", "invalid_choice", "owner_type must be 'show' or 'episode'")
    if not _owner_exists(db, owner_type, owner_id):
        raise AppValidationError.single(
            "owner_id", "not_found", f"No {owner_type} with id {owner_id}.", status_code=status.HTTP_404_NOT_FOUND
        )

    storage = get_storage()
    rows = db.execute(
        select(Artwork)
        .where(
            Artwork.owner_type == owner_type,
            Artwork.owner_id == owner_id,
        )
        .order_by(Artwork.kind)
    ).scalars().all()
    return [
        ArtworkOut(
            id=art.id,
            owner_type=art.owner_type.value,
            owner_id=art.owner_id,
            kind=art.kind.value,
            url=storage.url_for(art.storage_key),
            width=art.width,
            height=art.height,
            bytes=art.bytes,
            content_type=art.content_type,
            checksum=art.checksum,
        )
        for art in rows
    ]


@router.post(
    "/artwork",
    response_model=ArtworkOut,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ValidationErrorResponse}},
)
async def upload_artwork(
    file: UploadFile = File(...),
    kind: str = Form(...),
    owner_type: str = Form(...),
    owner_id: int = Form(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role(UserRole.editor, UserRole.admin)),
) -> ArtworkOut:
    if kind not in ARTWORK_SPECS:
        raise AppValidationError.single("kind", "invalid_choice", f"kind must be one of {list(ARTWORK_SPECS)}")
    if owner_type not in (ArtworkOwnerType.show.value, ArtworkOwnerType.episode.value):
        raise AppValidationError.single("owner_type", "invalid_choice", "owner_type must be 'show' or 'episode'")
    if not _owner_exists(db, owner_type, owner_id):
        raise AppValidationError.single(
            "owner_id", "not_found", f"No {owner_type} with id {owner_id}.", status_code=status.HTTP_404_NOT_FOUND
        )

    settings = get_settings()
    data = await file.read(settings.artwork_max_bytes + 1)  # bounded read: never buffer more than we'd accept anyway

    try:
        meta = validate_artwork(data, kind)
    except ArtworkValidationError as exc:
        raise AppValidationError([exc.as_dict()]) from None

    checksum = hashlib.sha256(data).hexdigest()
    ext = {"image/jpeg": "jpg", "image/png": "png"}.get(meta.content_type, "bin")
    storage_key = f"artwork/{owner_type}/{owner_id}/{kind}.{ext}"

    storage = get_storage()
    storage.put(storage_key, data, meta.content_type)

    existing = db.execute(
        select(Artwork).where(
            Artwork.owner_type == owner_type,
            Artwork.owner_id == owner_id,
            Artwork.kind == kind,
        )
    ).scalar_one_or_none()

    if existing is not None:
        if existing.storage_key != storage_key:
            storage.delete(existing.storage_key)
        existing.storage_key = storage_key
        existing.width = meta.width
        existing.height = meta.height
        existing.bytes = len(data)
        existing.content_type = meta.content_type
        existing.checksum = checksum
        existing.uploaded_by = user.id
        artwork = existing
    else:
        artwork = Artwork(
            owner_type=ArtworkOwnerType(owner_type),
            owner_id=owner_id,
            kind=ArtworkKind(kind),
            storage_key=storage_key,
            width=meta.width,
            height=meta.height,
            bytes=len(data),
            content_type=meta.content_type,
            checksum=checksum,
            uploaded_by=user.id,
        )
        db.add(artwork)

    db.commit()
    db.refresh(artwork)

    return ArtworkOut(
        id=artwork.id,
        owner_type=artwork.owner_type.value,
        owner_id=artwork.owner_id,
        kind=artwork.kind.value,
        url=storage.url_for(artwork.storage_key),
        width=artwork.width,
        height=artwork.height,
        bytes=artwork.bytes,
        content_type=artwork.content_type,
        checksum=artwork.checksum,
    )
