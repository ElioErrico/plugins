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


def _load_tools_status(path: Path = TOOLS_PATH) -> dict:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _save_tools_status(data: dict, path: Path = TOOLS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def _get_tool_name(cat=None) -> str:
    default_tool_name = "none"
    if cat is None:
        return default_tool_name

    try:
        settings = cat.mad_hatter.get_plugin().load_settings() or {}
        return str(settings.get("tool_name") or default_tool_name)
    except Exception:
        return default_tool_name


@hook
def fast_reply(fast_reply: dict, cat):
    user_message = cat.working_memory.user_message_json.text
    command = user_message.strip()
    if command not in {"crea_tool_07", "cancella_tool_07"}:
        return fast_reply

    tool_name = _get_tool_name(cat)
    ts = _load_tools_status()
    tools_cfg = ts.setdefault("tools", {})

    if command == "cancella_tool_07":
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

    existed = tool_name in tools_cfg
    tool_cfg = tools_cfg.setdefault(tool_name, {})
    if not isinstance(tool_cfg, dict):
        tool_cfg = {}
        tools_cfg[tool_name] = tool_cfg

    if not existed:
        _save_tools_status(ts)
        fast_reply["output"] = (
            f"Tool '{tool_name}' creato in tools_status.json."
        )
    else:
        fast_reply["output"] = (
            f"Tool '{tool_name}' già presente in tools_status.json."
        )

    return fast_reply
