# cat/plugins/CAT_doc_front_end_manager/filter_and_upload.py

from cat.mad_hatter.decorators import hook
from cat.log import log
from pathlib import Path
import json
import threading
from typing import Any, Dict, List, Optional
from cat.db.crud import get_users

# --- helper: file-lock cross-process + merge atomico ---
try:
    import fcntl
    _HAS_FCNTL = True
except Exception:
    _HAS_FCNTL = False


# === Costanti/risorse ===
USER_STATUS_PATH = Path("cat/static/user_status.json")
TAGS_PATH = Path("cat/static/tags.json")
_LOCK = threading.Lock()


# === I/O atomico su user_status.json ===
def _atomic_write_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    tmp.replace(path)


def _load_json_safe(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"[filter_and_upload] JSON load error on {path}: {e}")
        return default


def _update_user_status_atomic(mutator):
    """
    read-merge-write atomico di USER_STATUS_PATH sotto lock di file (se disponibile),
    altrimenti sotto lock di thread (_LOCK).
    """
    USER_STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not USER_STATUS_PATH.exists():
        _atomic_write_json(USER_STATUS_PATH, {})

    if _HAS_FCNTL:
        with open(USER_STATUS_PATH, "r+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.seek(0)
                raw = f.read()
                data = json.loads(raw) if raw.strip() else {}
            except Exception:
                data = {}
            new_data = mutator(data)

            tmp = USER_STATUS_PATH.with_suffix(USER_STATUS_PATH.suffix + ".tmp")
            with tmp.open("w", encoding="utf-8") as tf:
                json.dump(new_data, tf, indent=4, ensure_ascii=False)
            tmp.replace(USER_STATUS_PATH)
            fcntl.flock(f, fcntl.LOCK_UN)
    else:
        with _LOCK:
            data = _load_json_safe(USER_STATUS_PATH, {})
            new_data = mutator(data)
            _atomic_write_json(USER_STATUS_PATH, new_data)


# === Schema e normalizzazione ===
def _default_tag_obj() -> dict:
    return {
        "status": False,
        "documents": [],
        "prompt_list": [],      # es.: [{"prompt_title": "Default", "prompt_content": ""}]
        "selected_prompt": "",  # può contenere direttamente il contenuto, o il titolo
        "prompt": ""            # legacy (non usato per il prefix)
    }


def _load_tags_list() -> List[str]:
    data = _load_json_safe(TAGS_PATH, {})
    tags = data.get("tags", [])
    # normalizza a lista di stringhe (accetta int, converte a str)
    return [str(t) for t in tags if isinstance(t, (str, int))]

def _ensure_tag_fields(t: dict) -> dict:
    if not isinstance(t, dict):
        return _default_tag_obj()
    t.setdefault("status", bool(t.get("status", False)))
    t.setdefault("documents", t.get("documents", []) if isinstance(t.get("documents"), list) else [])
    t.setdefault("prompt_list", t.get("prompt_list", []) if isinstance(t.get("prompt_list"), list) else [])
    t.setdefault("selected_prompt", t.get("selected_prompt", "") or "")
    t.setdefault("prompt", t.get("prompt", "") or "")
    return t

def _ensure_user_status_schema(user_status: dict, tags: list[str]) -> dict:
    """
    Normalizza SOLO i tag già presenti per ciascun utente.
    NON aggiunge tag mancanti presi da tags.json.
    """
    for user, tagmap in list(user_status.items()):
        if not isinstance(tagmap, dict):
            user_status[user] = {}
            tagmap = user_status[user]

        for tag, obj in list(tagmap.items()):
            tagmap[tag] = _ensure_tag_fields(obj)

    return user_status



def _load_user_status_with_schema() -> dict:
    with _LOCK:
        user_status = _load_json_safe(USER_STATUS_PATH, {})
        tags = _load_tags_list()
        user_status = _ensure_user_status_schema(user_status, tags)
        # Non scrivere qui per non sovrascrivere update atomici concorrenti
        return user_status


def _resolve_selected_prompt(tag_obj: dict) -> Optional[str]:
    """
    Restituisce SOLO il contenuto deciso da selected_prompt, senza fallback a 'prompt'.

    Regole:
    - Se selected_prompt coincide con un 'prompt_content' presente in prompt_list -> usa quello (selected_prompt stesso).
    - Altrimenti se selected_prompt coincide con un 'prompt_title' -> ritorna il relativo 'prompt_content' (se non vuoto).
    - Altrimenti, se selected_prompt è una stringa non vuota -> consideralo già contenuto e usalo così com'è.
    - Se selected_prompt è vuoto -> None.
    """
    sel = (tag_obj.get("selected_prompt") or "").strip()
    if not sel:
        return None

    plist = tag_obj.get("prompt_list") or []

    # 1) match come contenuto
    for item in plist:
        if (item.get("prompt_content") or "").strip() == sel:
            return sel  # è già il contenuto scelto

    # 2) match come titolo
    for item in plist:
        if (item.get("prompt_title") or "").strip() == sel:
            content = (item.get("prompt_content") or "").strip()
            return content if content else None

    # 3) selected_prompt non è nel plist ma è valorizzato -> trattalo come contenuto diretto
    return sel


# === Sincronizzazione utenti/tag (opzionale, dipende dal tuo ambiente) ===
def aggiorna_users_tags():
    """
    Sincronizza *tutti* gli utenti esistenti con i tag in tags.json:
    - aggiunge utenti mancanti;
    - aggiunge tag mancanti agli utenti;
    - NON cancella tag esistenti non più presenti in tags.json;
    - non sovrascrive oggetti tag esistenti, integra solo i campi mancanti.
    """

    users_db = get_users()  # dict {user_id: {...}}  # noqa: F821 (presente altrove nel tuo progetto)
    users = [u["username"] for u in users_db.values() if "username" in u]

    with _LOCK:
        user_status = _load_json_safe(USER_STATUS_PATH, {})
        tags = _load_tags_list()  # FIX: era _tags_list()

        # assicurati che ogni utente esista
        for username in users:
            if username not in user_status or not isinstance(user_status.get(username), dict):
                user_status[username] = {}

            # integra tag per l'utente
            for tag in tags:
                if tag not in user_status[username] or not isinstance(user_status[username].get(tag), dict):
                    user_status[username][tag] = _default_tag_obj()
                else:
                    # completa campi mancanti
                    t = user_status[username][tag]
                    if "status" not in t:           t["status"] = bool(t.get("status", False))
                    if "documents" not in t:        t["documents"] = t.get("documents", [])
                    if "prompt_list" not in t:      t["prompt_list"] = t.get("prompt_list", [])
                    if "selected_prompt" not in t:  t["selected_prompt"] = t.get("selected_prompt", "")
                    if "prompt" not in t:           t["prompt"] = t.get("prompt", "")

        _atomic_write_json(USER_STATUS_PATH, user_status)


def _merge_sources_for_user_atomic(user: str, active_tags: List[str], sources: List[str]):
    """
    Inserisce in blocco i 'sources' nei tag attivi dell'utente.
    - Normalizza a basename
    - Aggiunge solo se non già presente
    - Nessuna gestione di duplicati con (2), (3) ...
    """
    sources = [Path(s).name for s in sources if isinstance(s, str) and s.strip()]

    def mutator(current: dict):
        user_map = current.setdefault(user, {})
        for tag in active_tags:
            tag_obj = user_map.setdefault(tag, _default_tag_obj())
            docs_list = tag_obj.get("documents", [])
            if not isinstance(docs_list, list):
                docs_list = []
            for s in sources:
                if s not in docs_list:
                    docs_list.append(s)
            tag_obj["documents"] = docs_list
            user_map[tag] = tag_obj
        current[user] = user_map
        return current

    _update_user_status_atomic(mutator)


@hook (priority=3)
def agent_prompt_prefix(prefix, cat):
    """
    - Se 'Cheshire' è già nel prefix originale:
        usa normalmente il primo selected_prompt valido (o il default).
    - Se 'Cheshire' NON è nel prefix originale:
        concatena il prefix originale con il risultato trovato (resolved o default).
    """

    default_prefix = "Rispondi alle domande dell'utente"

    # cat.send_ws_message(f"Prefix iniziale: {prefix}", "chat")

    try:
        user = cat.user_id
    except Exception:
        resolved = default_prefix
    else:
        user_status = _load_user_status_with_schema()
        tags_for_user = user_status.get(user, {})

        resolved = None
        for _, tag_obj in tags_for_user.items():
            if isinstance(tag_obj, dict) and tag_obj.get("status", False):
                candidate = _resolve_selected_prompt(tag_obj)
                if candidate:
                    # cat.send_ws_message(f"Prefix scelto da tag: {candidate}", "chat")
                    resolved = candidate
                    break

        if not resolved:
            resolved = default_prefix
            # cat.send_ws_message(f"Nessun tag attivo, uso default: {default_prefix}", "chat")

    resolved = "\n  ## Hard Skills \n" + resolved

    if prefix and str(prefix).strip():
        final_prefix = f"{prefix}\n\n{resolved}"
    else:
        final_prefix = resolved

    return final_prefix





# === Hook: metadati per recall (solo tag attivi + flag utente) ===
@hook  # default priority = 1
def before_cat_recalls_declarative_memories(declarative_recall_config, cat):
    """
    Inserisce nei metadati SOLO i tag attivi (True) + {user: True}.
    Robusto a chiavi/file mancanti.
    """
    try:
        user = cat.user_id
    except Exception:
        return declarative_recall_config

    user_status = _load_user_status_with_schema()
    tags_for_user = user_status.get(user, {})

    metadata = {}
    for tag, tag_obj in tags_for_user.items():
        if isinstance(tag_obj, dict) and tag_obj.get("status", False):
            metadata[tag] = True

    metadata[user] = True  # flag utente

    cfg = dict(declarative_recall_config or {})
    cfg["metadata"] = metadata
    log.critical(f'[filter_and_upload] metadata: {metadata}')
    return cfg


# === Hook: arricchisce metadata in upload e aggiorna elenco 'documents' ===
@hook
def before_rabbithole_stores_documents(docs, cat):
    try:
        user = cat.user_id
    except Exception:
        return docs

    user_status = _load_user_status_with_schema()
    tags_for_user = user_status.get(user, {})

    active_tags = [
        tag for tag, obj in tags_for_user.items()
        if isinstance(obj, dict) and obj.get("status", False)
    ]
    metadata_for_upload = {tag: True for tag in active_tags}
    metadata_for_upload[user] = True

    # DEBUG
    #cat.send_ws_message(f"[DBG] user={user}", "chat")
    #cat.send_ws_message(f"[DBG] active_tags={active_tags}", "chat")

    for doc in docs:
        current = dict(getattr(doc, "metadata", {}) or {})
        current.update(metadata_for_upload)
        doc.metadata = current
        #cat.send_ws_message(f"{str(doc.metadata)}", "chat")

        s = current.get("source")
        if not (isinstance(s, str) and s.strip()):
            continue
        s = Path(s.strip()).name  # FIX: salva sempre basename
        #cat.send_ws_message(f"{s}", "chat")

        def mutator(state: dict):
            user_map = state.setdefault(user, {})
            for tag in active_tags:
                tag_obj = user_map.setdefault(tag, _default_tag_obj())
                docs_list = tag_obj.get("documents", [])
                if not isinstance(docs_list, list):
                    docs_list = []
                if s not in docs_list:
                    docs_list.append(s)
                tag_obj["documents"] = docs_list
                user_map[tag] = tag_obj
            state[user] = user_map
            return state

        _update_user_status_atomic(mutator)

        # # DEBUG: verifica post-scrittura
        # try:
        #     state_after = _load_json_safe(USER_STATUS_PATH, {})
        #     for tag in active_tags:
        #         docs_list = (((state_after.get(user, {}) or {}).get(tag, {}) or {}).get("documents", []))
        #         # cat.send_ws_message(f"[DBG] documents[{user}][{tag}] = {docs_list}", "chat")
        # except Exception as e:
        #     # cat.send_ws_message(f"[DBG] readback error: {e}", "chat")

    return docs
