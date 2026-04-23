import json
import os
import shutil
from pathlib import Path

from model_catalog import get_default_model

APP_DIR = Path.home() / ".ai_thread_app"
APP_ROOT = Path(__file__).parent
LEGACY_PERSONAS_DIR = APP_ROOT / "data" / "personas"
LEGACY_OUTPUTS_DIR = APP_ROOT / "data" / "outputs"
PERSONAS_DIR = APP_DIR / "personas"
OUTPUTS_DIR = APP_DIR / "outputs"
CONFIG_FILE = APP_DIR / "config.json"

DEFAULT_CONFIG = {
    "keywords": ["AI", "LLM", "GPT", "Claude", "Gemini", "오픈소스 AI", "AI 툴"],
    "default_persona": "persona_default",
    "llm_provider": os.getenv("AI_THREAD_LLM_PROVIDER", "ollama"),
    "ollama_model": os.getenv("OLLAMA_MODEL", "gemma4:31b"),
    "openai_model": os.getenv("OPENAI_MODEL", get_default_model("openai")),
    "gemini_model": os.getenv("GEMINI_MODEL", get_default_model("gemini")),
    "theme_mode": os.getenv("AI_THREAD_THEME", "dark"),
}


def ensure_dirs():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    PERSONAS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    migrate_legacy_user_data()


def migrate_legacy_user_data():
    _copy_legacy_files(LEGACY_PERSONAS_DIR, PERSONAS_DIR, "*.json")
    _copy_legacy_files(LEGACY_OUTPUTS_DIR, OUTPUTS_DIR, "*.md")


def _copy_legacy_files(source_dir: Path, target_dir: Path, pattern: str):
    if not source_dir.exists():
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    for source in source_dir.glob(pattern):
        target = target_dir / source.name
        if not target.exists():
            shutil.copy2(source, target)


def load_config() -> dict:
    ensure_dirs()
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return {**DEFAULT_CONFIG, **json.load(f)}
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    ensure_dirs()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def list_personas() -> list[str]:
    PERSONAS_DIR.mkdir(parents=True, exist_ok=True)
    migrate_legacy_user_data()
    return sorted(p.stem for p in PERSONAS_DIR.glob("*.json"))


def load_persona(name: str) -> dict | None:
    ensure_dirs()
    path = PERSONAS_DIR / f"{name}.json"
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def save_persona(name: str, persona: dict):
    ensure_dirs()
    path = PERSONAS_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(persona, f, ensure_ascii=False, indent=2)
