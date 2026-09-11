from sqlalchemy import Enum, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PublishStatus
from app.models.mixins import TimestampMixin


class Show(TimestampMixin, Base):
    __tablename__ = "shows"
    __table_args__ = (Index("ix_shows_status_section", "status", "section"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    synopsis: Mapped[str | None] = mapped_column(Text)
    section: Mapped[str | None] = mapped_column(String(64))
    # Seed data carries several categories per show (see reference.json's category enum).
    # A JSONB array keeps the show/category relationship denormalized but query-able via
    # a GIN index, without a join table this scope doesn't otherwise need.
    categories: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[PublishStatus] = mapped_column(
        Enum(PublishStatus, native_enum=False, length=16, validate_strings=True),
        nullable=False,
        default=PublishStatus.draft,
    )

    seasons: Mapped[list["Season"]] = relationship(back_populates="show", cascade="all, delete-orphan")
