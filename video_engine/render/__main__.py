"""Compatibility entry point for the production Daily Astro renderer.

The repository still contains the previously stabilized renderer at
video_engine/render.py.  Python resolves this package directory for
`python -m video_engine.render`, so this entry point loads the legacy renderer
under a private module name, fixes the Hindi/English deity-key mismatch, and
then executes its existing production pipeline unchanged.
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


LEGACY_PATH = Path(__file__).resolve().parents[1] / "render.py"

spec = spec_from_file_location("video_engine._legacy_render", LEGACY_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load renderer: {LEGACY_PATH}")

legacy = module_from_spec(spec)
spec.loader.exec_module(legacy)

# RASHIS historically stores the human-facing Hindi deity name in field 3,
# while prepare_deities() returns paths keyed by the English asset key in
# field 4.  The old renderer indexed the path dictionary with field 3,
# producing KeyError: 'हनुमान जी'.  Normalize the runtime tuples so the
# existing visual labels remain Hindi while asset lookup uses stable keys.
legacy.RASHIS = [
    (key, label, deity_hi, asset_key)
    for key, label, deity_hi, asset_key in legacy.RASHIS
]

# Patch only the lookup performed by main(); create_scene still receives the
# Hindi devotional name and therefore keeps the intended visual text.
_original_main = legacy.main


def main():
    original_create_scene = legacy.create_scene

    def create_scene_compat(index, key, label, deity, deity_image, content):
        return original_create_scene(
            index,
            key,
            label,
            deity,
            deity_image,
            content,
        )

    legacy.create_scene = create_scene_compat

    # The legacy main indexes deity_paths with the Hindi name.  Replace
    # prepare_deities with an equivalent mapping that exposes both names,
    # while retaining the same local files and validation.
    original_prepare = legacy.prepare_deities

    def prepare_deities_compat():
        paths = original_prepare()
        expanded = dict(paths)
        for key, label, deity_hi, asset_key in legacy.RASHIS:
            expanded[deity_hi] = paths[asset_key]
        return expanded

    legacy.prepare_deities = prepare_deities_compat
    _original_main()


if __name__ == "__main__":
    main()
