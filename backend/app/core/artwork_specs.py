from dataclasses import dataclass


@dataclass(frozen=True)
class ArtworkSpec:
    aspect_w: int
    aspect_h: int
    target_w: int
    target_h: int

    @property
    def aspect_ratio(self) -> float:
        return self.aspect_w / self.aspect_h


# Mirrors _given/reference.json's artwork_specs. Duplicated here rather than read from
# _given/ at runtime because _given/ is challenge-provided fixture data, not something
# the deployed API should depend on existing on disk.
ARTWORK_SPECS: dict[str, ArtworkSpec] = {
    "poster": ArtworkSpec(aspect_w=2, aspect_h=3, target_w=600, target_h=900),
    "banner": ArtworkSpec(aspect_w=16, aspect_h=9, target_w=1280, target_h=720),
    "thumbnail": ArtworkSpec(aspect_w=16, aspect_h=9, target_w=640, target_h=360),
}

# Tolerance band, applied on top of the exact target_px above (see README for the reasoning):
# aspect must be within ±1% of the target aspect ratio; each dimension must be within
# [80%, 130%] of its target — wide enough that a reasonably-cropped upload passes, narrow
# enough to catch a thumbnail-sized image submitted as a banner.
ASPECT_TOLERANCE = 0.01
MIN_DIMENSION_RATIO = 0.8
MAX_DIMENSION_RATIO = 1.3
