import enum


class UserRole(str, enum.Enum):
    editor = "editor"
    admin = "admin"


class PublishStatus(str, enum.Enum):
    """Shared by shows and episodes: draft content is never emitted to the catalogue."""

    draft = "draft"
    published = "published"


class ArtworkOwnerType(str, enum.Enum):
    show = "show"
    episode = "episode"


class ArtworkKind(str, enum.Enum):
    poster = "poster"
    banner = "banner"
    thumbnail = "thumbnail"


class PublishRunStatus(str, enum.Enum):
    running = "running"
    success = "success"
    failed = "failed"
