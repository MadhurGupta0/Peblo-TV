# Mirrors _given/reference.json's `sections` order. Duplicated here for the same reason
# as artwork_specs.py: the deployed API shouldn't depend on _given/ existing on disk.
# Determines the catalogue's top-level ordering; a section with no publishable shows is
# simply omitted, never emitted empty.
SECTION_ORDER: list[str] = ["featured", "series", "minisodes", "songs"]
