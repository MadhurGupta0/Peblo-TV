import datetime as dt

from sqlalchemy import DateTime, Enum, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import PublishRunStatus


class PublishRun(Base):
    __tablename__ = "publish_runs"
    __table_args__ = (
        # Enforces "only one publish in flight at a time" at the DB level (belt-and-braces
        # alongside the advisory lock taken in the publish service).
        Index(
            "uq_publish_runs_one_running",
            "status",
            unique=True,
            postgresql_where=text("status = 'running'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(nullable=False)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[PublishRunStatus] = mapped_column(
        Enum(PublishRunStatus, native_enum=False, length=16, validate_strings=True), nullable=False
    )
    counts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    catalogue_key: Mapped[str | None] = mapped_column(String(512))
    error: Mapped[str | None] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(String(64))
