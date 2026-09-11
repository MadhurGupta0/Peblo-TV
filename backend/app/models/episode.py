from sqlalchemy import Enum, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import PublishStatus
from app.models.mixins import TimestampMixin


class Episode(TimestampMixin, Base):
    __tablename__ = "episodes"
    __table_args__ = (
        UniqueConstraint("season_id", "episode_number", "language", name="uq_episodes_season_number_language"),
        Index("ix_episodes_content_group", "content_group"),
        # Partial unique index: content_group ties language variants of one episode together;
        # NULL content_group means "no variants" and must not collide with anything.
        Index(
            "uq_episodes_content_group_language",
            "content_group",
            "language",
            unique=True,
            postgresql_where=text("content_group IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    episode_number: Mapped[int] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    synopsis: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[int | None] = mapped_column()
    language: Mapped[str] = mapped_column(String(8), nullable=False)
    content_group: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[PublishStatus] = mapped_column(
        Enum(PublishStatus, native_enum=False, length=16, validate_strings=True),
        nullable=False,
        default=PublishStatus.draft,
    )

    season: Mapped["Season"] = relationship(back_populates="episodes")
