from pathlib import Path


def _sanitize_name(name: str) -> str:
    return Path(name).name


def load_prompt(name: str, category: str = "system") -> str:
    """
    Dynamically loads an .md prompt file from the designated category folder.
    Falls back to 'default.md' if the specified file does not exist.
    """
    name = _sanitize_name(name)
    base_dir = Path(f"app/prompts/{category}")
    target_path = base_dir / f"{name}.md"

    if target_path.exists():
        return target_path.read_text(encoding="utf-8")

    fallback_path = base_dir / "default.md"
    if fallback_path.exists():
        return fallback_path.read_text(encoding="utf-8")

    return ""


def save_prompt(name: str, content: str, category: str = "system") -> None:
    name = _sanitize_name(name)
    base_dir = Path(f"app/prompts/{category}")
    base_dir.mkdir(parents=True, exist_ok=True)
    target_path = base_dir / f"{name}.md"
    target_path.write_text(content, encoding="utf-8")


def delete_prompt(name: str, category: str = "system") -> bool:
    name = _sanitize_name(name)
    target_path = Path(f"app/prompts/{category}") / f"{name}.md"
    if not target_path.exists():
        return False
    target_path.unlink()
    return True


def get_available_prompts(category: str = "system") -> list[str]:
    """
    Scans the prompt directory and returns a clean list of available .md names.
    Perfect for populating the front-end dropdown menu.
    """
    dir_path = Path(f"app/prompts/{category}")
    if not dir_path.exists():
        return []

    return sorted(
        [f.stem for f in dir_path.glob("*.md") if not f.name.startswith("__")]
    )
