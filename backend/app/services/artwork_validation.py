import io
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from app.core.artwork_specs import ARTWORK_SPECS, ASPECT_TOLERANCE, MAX_DIMENSION_RATIO, MIN_DIMENSION_RATIO
from app.core.config import get_settings


class ArtworkValidationError(Exception):
    def __init__(self, field: str, code: str, message: str) -> None:
        self.field = field
        self.code = code
        self.message = message
        super().__init__(message)

    def as_dict(self) -> dict:
        return {"field": self.field, "code": self.code, "message": self.message}


@dataclass(frozen=True)
class ArtworkMeta:
    width: int
    height: int
    content_type: str


def validate_artwork(data: bytes, kind: str) -> ArtworkMeta:
    settings = get_settings()
    spec = ARTWORK_SPECS[kind]

    if len(data) > settings.artwork_max_bytes:
        actual_kb = len(data) / 1024
        max_kb = settings.artwork_max_bytes / 1024
        raise ArtworkValidationError(
            field=kind,
            code="size_too_large",
            message=f"This {kind} is {actual_kb:.0f} KB. The maximum allowed size is {max_kb:.0f} KB. Try compressing it.",
        )

    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
        image = Image.open(io.BytesIO(data))  # verify() consumes the file handle; reopen to actually read pixels
        width, height = image.size
        content_type = Image.MIME.get(image.format, "application/octet-stream")
    except (UnidentifiedImageError, OSError, ValueError):
        raise ArtworkValidationError(
            field=kind,
            code="invalid_image",
            message="We couldn't read this file as an image. Please upload a JPEG or PNG.",
        ) from None

    actual_aspect = width / height
    target_aspect = spec.aspect_ratio
    if abs(actual_aspect - target_aspect) / target_aspect > ASPECT_TOLERANCE:
        orientation = "portrait" if spec.aspect_w < spec.aspect_h else "landscape"
        crop_hint = "cropping it taller" if actual_aspect > target_aspect else "cropping it wider"
        raise ArtworkValidationError(
            field=kind,
            code="aspect_mismatch",
            message=(
                f"This {kind} is {width}×{height}. {kind.capitalize()}s must be {orientation}, "
                f"about {spec.target_w}×{spec.target_h} ({spec.aspect_w}:{spec.aspect_h}). "
                f"Try {crop_hint}."
            ),
        )

    min_w, max_w = spec.target_w * MIN_DIMENSION_RATIO, spec.target_w * MAX_DIMENSION_RATIO
    min_h, max_h = spec.target_h * MIN_DIMENSION_RATIO, spec.target_h * MAX_DIMENSION_RATIO
    if not (min_w <= width <= max_w and min_h <= height <= max_h):
        size_hint = "a larger image" if width < spec.target_w else "a smaller image"
        raise ArtworkValidationError(
            field=kind,
            code="dimension_out_of_range",
            message=(
                f"This {kind} is {width}×{height}. {kind.capitalize()}s should be about "
                f"{spec.target_w}×{spec.target_h}. Try uploading {size_hint}."
            ),
        )

    return ArtworkMeta(width=width, height=height, content_type=content_type)
