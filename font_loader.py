import ctypes
import os
from pathlib import Path

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
UI_FONT_FAMILY = "Moneygraphy Rounded"
FALLBACK_FONT_FAMILY = "Malgun Gothic"

_loaded = False


def load_bundled_fonts() -> int:
    global _loaded
    if _loaded or not FONT_DIR.exists():
        return 0

    font_paths = sorted(FONT_DIR.glob("*.otf")) + sorted(FONT_DIR.glob("*.ttf"))
    if not font_paths:
        _loaded = True
        return 0
    if os.name != "nt":
        _loaded = True
        return 0

    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    loaded_count = 0
    for font_path in font_paths:
        # FR_PRIVATE makes optional local fonts available to this app process only.
        if gdi32.AddFontResourceExW(str(font_path), 0x10, 0):
            loaded_count += 1

    _loaded = True
    return loaded_count


def get_ui_font_family() -> str:
    return UI_FONT_FAMILY if load_bundled_fonts() else FALLBACK_FONT_FAMILY
