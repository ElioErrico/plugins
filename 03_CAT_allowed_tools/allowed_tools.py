import json
import os
from pathlib import Path

from cat.mad_hatter.decorators import hook


def _resolve_static_file(filename: str) -> Path:
    plugin_cat_dir = Path(__file__).resolve().parents[2]
    candidates = []

    ccat_root = os.environ.get("CCAT_ROOT")
    if ccat_root:
        candidates.append(Path(ccat_root) / "cat" / "static" / filename)

    candidates.append(plugin_cat_dir / "static" / filename)
    candidates.append(Path.cwd() / "cat" / "static" / filename)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0] if ccat_root else candidates[1]


TOOLS_PATH = _resolve_static_file("tools_status.json")
STATUS_PATH = _resolve_static_file("user_status.json")


# ----------------------- helpers -----------------------

def _load_tools_status(path: Path = TOOLS_PATH) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def get_enabled_tools(cat, path: Path = TOOLS_PATH):
    ts = _load_tools_status(path)
    uid = str(getattr(cat, "user_id", "") or "")

    tools_cfg = ts.get("tools", {})
    enabled_tools = []

    for cfg in tools_cfg.values():
        if not bool(cfg.get("user_id_tool_status", {}).get(uid, False)):
            continue

        for technical_name in cfg.get("tools_list_technical_name", []):
            technical_name = str(technical_name or "").strip()
            if technical_name and technical_name not in enabled_tools:
                enabled_tools.append(technical_name)
    return enabled_tools

def _load_user_status(path: Path = STATUS_PATH) -> dict:
    """Carica user_status.json in modo robusto."""
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _get_selected_tag_for_user(uid: str, user_status: dict) -> str | None:
    """
    Restituisce il nome del primo tag con status=True per l'utente uid.
    Se non c'è alcun tag attivo, ritorna None.
    """
    tags_for_user = user_status.get(uid, {})
    if isinstance(tags_for_user, dict):
        for tag_name, tag_obj in tags_for_user.items():
            if isinstance(tag_obj, dict) and tag_obj.get("status", False):
                return tag_name
    return None


# ----------------------- hooks -----------------------

@hook(priority=3)
def agent_prompt_prefix(prefix, cat):
    """
    Prepara l'intestazione generale del prompt e mantiene il prefix
    già composto dai plugin precedenti.
    """

    # Carica settings dal plugin
    settings = cat.mad_hatter.get_plugin().load_settings()
    header = (
        settings["prompt_prefix_incipit"]
        + "\n"
        + settings["tool_orchestration_header"]
    )

    if prefix and prefix.strip():
        return f"{header}\n{prefix}"

    return header

