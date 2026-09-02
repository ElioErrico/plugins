# helpers.py

from typing import Tuple, Optional, List, Dict
from urllib.parse import quote_plus, urlparse, parse_qs, unquote
import subprocess
import asyncio
import json
import re

# --- Markdown strip robusto (fallback se "strip_markdown" non è installato) ---
try:
    from strip_markdown import strip_markdown as _strip_md
except Exception:
    def _strip_md(s: str) -> str:
        # fallback minimale: rimuove i simboli markdown più comuni
        s = re.sub(r"[*_`>#~\-]", " ", s)
        s = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1 \2", s)  # [titolo](url) → "titolo url"
        s = re.sub(r"\s+", " ", s)
        return s.strip()


# =========== DUCKDUCKGO URL BUILDERS ===========

def duckduckgo_serp_url_from_query(query: str, *, kl: Optional[str] = "it-it", kp: Optional[str] = "-1", html_variant: bool = True) -> str:
    """Costruisce l'URL SERP DDG dalla query 'plain'."""
    q = " ".join((query or "").split())
    if html_variant:
        base = "https://html.duckduckgo.com/html/"
    else:
        base = "https://duckduckgo.com/"
    params = f"?q={quote_plus(q)}"
    if kl: params += f"&kl={quote_plus(kl)}"
    if kp: params += f"&kp={quote_plus(kp)}"
    return base + params

def duckduckgo_serp_url_from_md(md: str, *, kl: Optional[str] = "it-it", kp: Optional[str] = "-1", html_variant: bool = True) -> str:
    """Accetta una query in Markdown, la 'sbuccia' e crea la SERP URL."""
    plain = " ".join(_strip_md(md).split())
    return duckduckgo_serp_url_from_query(plain, kl=kl, kp=kp, html_variant=html_variant)


# =========== CLI CRAWL (crwl) ===========

def crwl_markdown(url: str, *, crawler_cfg: Optional[str] = None, filter_cfg: Optional[str] = None, fit: bool = False) -> Tuple[bool, str, str, int]:
    """
    Esegue: crwl <url> [-C cfg] [-f filter] -o (markdown|markdown-fit)
    Ritorna: (ok, stdout, stderr, returncode)
    """
    try:
        cmd = ["crwl", url]
        if crawler_cfg:
            cmd += ["-C", crawler_cfg]
        if filter_cfg:
            cmd += ["-f", filter_cfg]
        cmd += ["-o", "markdown-fit" if fit else "markdown"]

        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        ok = (proc.returncode == 0) and bool(out)
        return ok, out, err, proc.returncode
    except FileNotFoundError:
        return False, "", "Comando `crwl` non trovato (esegui `crawl4ai-setup`).", -1
    except Exception as e:
        return False, "", f"Errore inatteso: {e}", -2


# =========== API CRAWL (preferisce fit_markdown) ===========

def crawl_markdown_api(
    url: str,
    *,
    prefer: str = "fit",  # "fit" | "citations" | "raw"
    excluded_tags = ("form","header","footer","nav","aside"),
    css_selector: Optional[str] = "main, article, #main, .main, .content, .post-content",
    table_score_threshold: int = 7,
    citations: bool = False,
) -> Tuple[bool, str, str]:
    """
    Usa AsyncWebCrawler + DefaultMarkdownGenerator e ritorna (ok, markdown_text, err).
    Preferisce fit_markdown se disponibile.
    """
    async def _run():
        try:
            from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
            from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        except Exception as e:
            return False, "", f"crawl4ai non disponibile: {e}"

        gen = DefaultMarkdownGenerator(options={"citations": citations, "body_width": 80})
        cfg = CrawlerRunConfig(
            excluded_tags=list(excluded_tags),
            css_selector=css_selector,
            table_score_threshold=table_score_threshold,
            markdown_generator=gen,
        )
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url, config=cfg)

        md_text = ""
        md = result.markdown
        if isinstance(md, str):
            md_text = md
        elif md:
            if prefer == "fit" and getattr(md, "fit_markdown", None):
                md_text = md.fit_markdown
            elif prefer == "citations" and getattr(md, "markdown_with_citations", None):
                md_text = md.markdown_with_citations
            else:
                md_text = getattr(md, "raw_markdown", "") or getattr(md, "references_markdown", "") or ""

        ok = bool(result.success and (md_text or "").strip())
        return ok, (md_text or "").strip(), (result.error_message or "")

    try:
        return asyncio.run(_run())
    except RuntimeError:
        # Event loop già attivo: fai fallback al CLI “semplice”
        ok, out, err, _ = crwl_markdown(url)
        return ok, out, err or "Event loop attivo: fallback CLI."


# =========== DUCKDUCKGO SERP → JSON STRUTTURATO ===========

def _ddg_unwrap(href: str) -> str:
    """/l/?uddg=<url> → URL reale."""
    try:
        p = urlparse(href)
        if p.netloc.endswith("duckduckgo.com") and p.path.startswith("/l/"):
            qs = parse_qs(p.query)
            if "uddg" in qs and qs["uddg"]:
                return unquote(qs["uddg"][0])
        return href
    except Exception:
        return href

def _normalize_item(title: str, url_raw: str, snippet: str) -> Dict[str, str]:
    return {
        "title": (title or "").strip(),
        "url": _ddg_unwrap((url_raw or "").strip()),
        "description": (snippet or "").strip(),
    }

def _looks_like_urlish(text: str) -> bool:
    """Riconosce stringhe tipo URL/domìnio usate come 'descrizione' in SERP."""
    t = (text or "").strip()
    if not t:
        return False
    return bool(re.match(r"^(https?://|www\.[\w.-]+/|[\w.-]+\.[a-z]{2,}/)", t, flags=re.I))

def _fetch_meta_description_sync(url: str, timeout: int = 10) -> str:
    """Scarica la pagina e prova a estrarre la meta description/og:description."""
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # priorità: og:description > twitter:description > name=description
        md = soup.select_one("meta[property='og:description'][content]")
        if md and md.get("content"):
            return md["content"].strip()
        md = soup.select_one("meta[name='twitter:description'][content]")
        if md and md.get("content"):
            return md["content"].strip()
        md = soup.select_one("meta[name='description'][content]")
        if md and md.get("content"):
            return md["content"].strip()
        return ""
    except Exception:
        return ""

def _ddg_scrape_sync(url: str, limit: int) -> List[Dict[str, str]]:
    """Fallback: requests + BeautifulSoup (markup HTML statico di DDG)."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except Exception as e:
        raise RuntimeError(f"Dependencies mancanti per fallback sync: {e}")

    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items: List[Dict[str, str]] = []
    for res in soup.select("div.result"):
        a = res.select_one("a.result__a")
        if not a:
            continue
        title = a.get_text(" ", strip=True)
        href = a.get("href", "")

        # SOLO snippet vero (niente .result__extras che contiene anche l'URL visuale)
        snippet_el = res.select_one(".result__snippet") or res.select_one(".result__snippet.js-result-snippet")
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""

        items.append(_normalize_item(title, href, snippet))
        if len(items) >= limit:
            break
    return items

async def _ddg_extract_with_crawl4ai(url: str, limit: int) -> List[Dict[str, str]]:
    """Preferred: Crawl4AI + JsonCssExtractionStrategy per estrarre (title, href, snippet)."""
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, JsonCssExtractionStrategy
    except Exception:
        return []

    schema = {
        "name": "DuckDuckGo SERP",
        "baseSelector": "div.result",
        "fields": [
            {"name": "title", "selector": "a.result__a", "type": "text"},
            {"name": "href", "selector": "a.result__a", "type": "attribute", "attribute": "href"},
            # FIX: usiamo SOLO i selettori snippet, niente extras
            {"name": "snippet", "selector": ".result__snippet, .result__snippet.js-result-snippet", "type": "text"},
        ],
        "limit": limit
    }

    cfg = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        only_text=False,
        markdown_generator=None,
        extraction_strategy=JsonCssExtractionStrategy(schema),
        excluded_tags=["header", "footer", "nav", "aside", "form"],
        css_selector="main, #links, .content-wrap, .serp__results",
        word_count_threshold=0,
        verbose=False,
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url, config=cfg)

    items: List[Dict[str, str]] = []
    if getattr(result, "success", False) and getattr(result, "extracted_content", None):
        try:
            data = json.loads(result.extracted_content)
            for row in data[:limit]:
                items.append(_normalize_item(row.get("title",""), row.get("href",""), row.get("snippet","")))
        except Exception:
            pass
    return items

def ddg_search_structured(query_or_md: str, *, limit: int = 8, kl: str = "it-it", kp: str = "-1") -> Tuple[bool, List[Dict[str, str]], str]:
    """
    Ritorna (ok, results, err) con results = [{"title","url","description"}, ...].
    La 'description' è lo snippet della SERP; se vuoto o 'URL-like', prova ad arricchirla
    con la meta description della pagina (solo sui primi 4 risultati per efficienza).
    """
    try:
        url = duckduckgo_serp_url_from_md(query_or_md, kl=kl, kp=kp, html_variant=True)
        try:
            items = asyncio.run(_ddg_extract_with_crawl4ai(url, limit))
        except RuntimeError:
            # event loop già attivo → fallback sync
            items = _ddg_scrape_sync(url, limit)

        if not items:
            # Tentativo finale: fallback sync esplicito
            try:
                items = _ddg_scrape_sync(url, limit)
            except Exception as e2:
                return False, [], f"Fallback sync error: {e2}"
            if not items:
                return False, [], "Nessun risultato estratto."

        # Enrichment controllato
        to_enrich = min(4, len(items))  # riduci chiamate extra
        for i in range(to_enrich):
            desc = items[i].get("description", "")
            if not desc or _looks_like_urlish(desc):
                meta = _fetch_meta_description_sync(items[i].get("url",""))
                if meta:
                    items[i]["description"] = meta

        return True, items, ""
    except Exception as e:
        return False, [], f"Errore DDG: {e}"


# (opzionale) aiuta l'intellisense/lettura
__all__ = [
    "duckduckgo_serp_url_from_query",
    "duckduckgo_serp_url_from_md",
    "crwl_markdown",
    "crawl_markdown_api",
    "ddg_search_structured",
]
