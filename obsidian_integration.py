import json
import os
import shutil
import webbrowser
from pathlib import Path
from urllib.parse import quote


def discover_obsidian_vaults() -> list[dict]:
    config_path = Path(os.environ.get("APPDATA", "")) / "Obsidian" / "obsidian.json"
    if not config_path.exists():
        return []

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    vaults = []
    for vault_id, vault in (data.get("vaults") or {}).items():
        path = Path(vault.get("path", ""))
        if not path.exists() or not path.is_dir():
            continue
        vaults.append({
            "id": vault_id,
            "name": path.name,
            "path": path,
            "open": bool(vault.get("open")),
            "ts": int(vault.get("ts") or 0),
        })

    return sorted(vaults, key=lambda item: (not item["open"], -item["ts"]))


def copy_markdown_to_obsidian_vault(markdown_path: Path, folder_name: str = "AI Thread App") -> tuple[dict, Path, Path]:
    vaults = discover_obsidian_vaults()
    if not vaults:
        raise RuntimeError("Obsidian vault를 찾지 못했습니다. Obsidian에서 vault를 한 번 열어주세요.")

    markdown_path = Path(markdown_path)
    if not markdown_path.exists():
        raise FileNotFoundError(markdown_path)

    vault = vaults[0]
    target_dir = vault["path"] / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / markdown_path.name
    shutil.copy2(markdown_path, target_path)
    relative_path = target_path.relative_to(vault["path"])
    return vault, relative_path, target_path


def build_obsidian_open_uri(vault_name: str, file_path: Path) -> str:
    normalized_file = file_path.as_posix()
    return f"obsidian://open?vault={quote(vault_name)}&file={quote(normalized_file)}"


def open_markdown_in_obsidian(markdown_path: Path) -> tuple[bool, str]:
    vault, relative_path, target_path = copy_markdown_to_obsidian_vault(markdown_path)
    uri = build_obsidian_open_uri(vault["name"], relative_path)
    opened = webbrowser.open(uri)
    if not opened and os.name == "nt":
        os.startfile(target_path)
    return opened, str(target_path)
