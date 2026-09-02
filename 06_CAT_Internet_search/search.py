# search.py

from typing import Dict
from cat.mad_hatter.decorators import hook
from cat.mad_hatter.decorators import tool

from cat.looking_glass.stray_cat import StrayCat
from cat.log import log
import json

from .helpers import (
    crwl_markdown,
    crawl_markdown_api,
    ddg_search_structured,
)


@hook  # default priority = 1 
def before_cat_reads_message(user_message_json, cat):
    """
    Hook che aggiunge un prompt di pianificazione a tutti i messaggi quando il tool è abilitato.
    Questo garantisce che la prima azione dell'agente sia sempre la pianificazione.
    """
    settings = cat.mad_hatter.get_plugin().load_settings()
    tool_key = settings["tool_name"]    
    
    # ---- Guard: abilita/disabilita tool per utente; fallback=False ----
    try:
        with open("cat/static/tools_status.json", "r", encoding="utf-8") as f:
            ts = json.load(f) or {}
    except Exception:
        ts = {}

    uid = str(getattr(cat, "user_id", "") or "")
    enabled = bool(
        ts.get("tools", {})
          .get(tool_key, {})
          .get("user_id_tool_status", {})
          .get(uid, False)
    )
    # cat.send_ws_message(f"Tool {tool_key} enabled for user {uid}","chat")
    if not enabled:
        # cat.send_ws_message(f"Tool {tool_key} not enabled for user {uid}","chat")
        return user_message_json

    # Prompt di pianificazione che verrà aggiunto a tutte le richieste
    planning_phase_prompt = """\n - Se necessario ai fini della tua richiesta utilizza il tool duck_duck_go_search per cercare informazioni online e una volta ottenuto il link utilizza il tool crawl_site_content per leggere il contenuto di un sito web."""

    user_message_json["text"] = user_message_json["text"] + planning_phase_prompt
    return user_message_json

@tool (return_direct=False)
def duck_duck_go_search(tool_input: str, cat):
    """
    Use this tool when you need to search informations Online.
    tool_input: the query (plain or markdown)
    return: a JSON array of results: [{"title","url","description"}, ...]
    """
    query = (tool_input or "").strip()
    if not query:
        return (
            "Errore: query vuota.\n"
            "Usa questo tool passando una query, ad es.: "
            "duck_duck_go_search('**cheshire cat** hooks reference before_cat_reads_message')"
        )

    ok, results, err = ddg_search_structured(query, limit=8, kl="it-it", kp="-1")
    if ok:
        return json.dumps(results, ensure_ascii=False, indent=2)
    else:
        log.error(f"DDG structured search failed: {err}")
        return f"Ricerca DDG non riuscita. Dettagli: {err}"

@tool(return_direct=False)
def crawl_site_content(tool_input: str, cat):
    """
    Use this tool when you need to read a web page.
    Input: tool_input = URL (with or without scheme)
    Output: Web page content.
    """
    url = (tool_input or "").strip()
    if not url:
        return (
            "Errore: URL mancante.\n"
            "Esempio: crawl_site_content('https://example.com/page')"
        )

    # Aggiunge lo schema se assente (supporta anche raw://)
    if not url.lower().startswith(("http://", "https://", "raw://")):
        url = "https://" + url

    # 1) API Crawl4AI → preferisci fit_markdown
    ok, md, err = crawl_markdown_api(
        url,
        prefer="fit",
        excluded_tags=("form", "header", "footer", "nav", "aside"),
        css_selector="main, article, #main, .main, .content, .post-content, [role='main']",
        table_score_threshold=7,
        citations=False,
    )

    # 2) Fallback CLI (markdown-fit) se API fallisce
    if not ok or not md:
        ok2, out, err2, code = crwl_markdown(url, fit=True)
        if ok2 and out:
            md = out
        else:
            log.error(f"crawl_site_content failed. API: {err} | CLI: code {code}, err: {err2}")
            return f"Estrazione non riuscita.\nAPI: {err}\nCLI: {err2 or f'exit code {code}'}"

    # 3) Troncamento prudente per evitare risposte eccessive
    MAX_CHARS = 30000
    if len(md) > MAX_CHARS:
        md = md[:MAX_CHARS].rsplit("\n", 1)[0] + "\n\n…[troncato]"

    return md




