from sqlalchemy import Enum, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import ArtworkKind, ArtworkOwnerType
from app.models.mixins import TimestampMixin


class Artwork(TimestampMixin, Base):
    __tablename__ = "artwork"
    __table_args__ = (Index("ix_artwork_owner_kind", "owner_type", "owner_id", "kind"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # Polymorphic owner (show or episode) instead of two nullable FKs — artwork rows are
    # identical in shape regardless of owner, and the "has artwork?" check is one query either way.
    owner_type: Mapped[ArtworkOwnerType] = mapped_column(
        Enum(ArtworkOwnerType, native_enum=False, length=16, validate_strings=True), nullable=False
    )
    owner_id: Mapped[int] = mapped_column(nullable=False)
    kind: Mapped[ArtworkKind] = mapped_column(
        Enum(ArtworkKind, native_enum=False, length=16, validate_strings=True), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    width: Mapped[int] = mapped_column(nullable=False)
    height: Mapped[int] = mapped_column(nullable=False)
    bytes: Mapped[int] = mapped_column(nullable=False)
    content_type: Mapped[str] = mapped_column(String(64), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by: Mapped[int | None] = mapped_column()
