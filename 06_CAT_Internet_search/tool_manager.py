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

def _load_tools_status(path: Path = TOOLS_PATH) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _get_tool_name(cat=None) -> str:
    default_tool_name = "none"
    if cat is None:
        return default_tool_name

    try:
        settings = cat.mad_hatter.get_plugin().load_settings() or {}
        return str(settings.get("tool_name") or default_tool_name)
    except Exception:
        return default_tool_name


def _get_current_plugin_technical_names(cat) -> list[str]:
    if cat is None:
        return []

    try:
        plugin = cat.mad_hatter.get_plugin()
        technical_names = []
        for tool in getattr(plugin, "tools", []):
            technical_name = str(getattr(tool, "name", "") or "").strip()
            if technical_name and technical_name not in technical_names:
                technical_names.append(technical_name)
        return technical_names
    except Exception:
        return []

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

def _save_tools_status(data: dict, path: Path = TOOLS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@hook
def fast_reply(fast_reply: dict, cat):
    user_message = cat.working_memory.user_message_json.text
    command = user_message.strip()
    if command not in {"crea_tool_06", "cancella_tool_06"}:
        return fast_reply

    tool_name = _get_tool_name(cat)
    ts = _load_tools_status()
    tools_cfg = ts.setdefault("tools", {})

    if command == "cancella_tool_06":
        existed = tool_name in tools_cfg
        if existed:
            del tools_cfg[tool_name]
            _save_tools_status(ts)
            fast_reply["output"] = (
                f"Tool '{tool_name}' cancellato da tools_status.json."
            )
        else:
            fast_reply["output"] = (
                f"Tool '{tool_name}' non presente in tools_status.json."
            )
        return fast_reply

    technical_names = _get_current_plugin_technical_names(cat)
    existed = tool_name in tools_cfg
    tool_cfg = tools_cfg.setdefault(tool_name, {})
    if not isinstance(tool_cfg, dict):
        tool_cfg = {}
        tools_cfg[tool_name] = tool_cfg

    changed = tool_cfg.get("tools_list_technical_name") != technical_names
    tool_cfg["tools_list_technical_name"] = technical_names

    if (not existed) or changed:
        _save_tools_status(ts)

    if not existed:
        fast_reply["output"] = (
            f"Tool '{tool_name}' creato in tools_status.json con tools_list_technical_name={technical_names}."
        )
    elif changed:
        fast_reply["output"] = (
            f"Tool '{tool_name}' aggiornato in tools_status.json con tools_list_technical_name={technical_names}."
        )
    else:
        fast_reply["output"] = (
            f"Tool '{tool_name}' già presente in tools_status.json con tools_list_technical_name={technical_names}."
        )

    return fast_reply

@hook  # default priority = 1
def agent_allowed_tools(allowed_tools, cat):
    enabled_tools = get_enabled_tools(cat)
    # cat.send_ws_message(f"Enabled tools from 06 CAT_Internet_search: {str(enabled_tools)}", "chat")
    return enabled_tools


@hook(priority=4)
def agent_prompt_prefix(prefix, cat):
    enabled_tools = get_enabled_tools(cat)
    settings = cat.mad_hatter.get_plugin().load_settings() or {}
    prompt_lines = []

    if "duck_duck_go_search" in enabled_tools:
        prompt_line = (settings.get("duck_duck_go_search_description") or "").strip()
        if prompt_line:
            prompt_lines.append(prompt_line)

    if "crawl_site_content" in enabled_tools:
        prompt_line = (settings.get("crawl_site_content_description") or "").strip()
        if prompt_line:
            prompt_lines.append(prompt_line)

    if not prompt_lines:
        return prefix

    return prefix + "\n\n" + "\n".join(prompt_lines)


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
