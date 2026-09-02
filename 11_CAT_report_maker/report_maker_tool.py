from cat.mad_hatter.decorators import tool
from cat.log import log
from docx import Document
import os
import json
from datetime import datetime
import traceback
from pathlib import Path

# Import dei moduli helper
from .report_prompts import get_prompt_by_type
from .report_formatters import (
    parse_markdown_to_word,
    load_template_document
)

# ===== PERCORSI =====
PLUGIN_DIR = os.path.dirname(__file__)
REPORT_TYPES_CONFIG_PATH = os.path.join(PLUGIN_DIR, "report_types_config.json")


def _resolve_static_file(filename: str) -> Path:
    """Risolve un file statico del core senza dipendere dalla working directory."""
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


TOOLS_STATUS_PATH = _resolve_static_file("tools_status.json")


def get_static_url():
    """Restituisce l'URL base per i file statici"""
    return "/static/"


# ===== FUNZIONI HELPER =====

def load_report_types_config():
    """
    Carica la configurazione dei tipi di report dal file JSON.
    
    Returns:
        dict: Configurazione dei tipi di report
    """
    try:
        with open(REPORT_TYPES_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Error loading report types config: {e}")
        return {
            "report_types": [{"key": "standard", "label": "Standard Report"}],
            "default_report_type": "standard"
        }


def get_valid_report_types():
    """
    Restituisce la lista dei tipi di report validi.
    
    Returns:
        list[str]: Lista delle chiavi valide (es. ["standard", "technical", ...])
    """
    config = load_report_types_config()
    return [rt["key"] for rt in config.get("report_types", [])]


def get_user_report_type(user_id: str, tool_key: str):
    """
    Recupera il tipo di report configurato per l'utente da tools_status.json.
    
    Args:
        user_id: ID dell'utente
        tool_key: Chiave del tool (es. "Report Maker")
    
    Returns:
        str: Tipo di report (es. "standard", "technical", ecc.)
    """
    try:
        # Legge tools_status.json
        with TOOLS_STATUS_PATH.open("r", encoding="utf-8") as f:
            tools_status = json.load(f)
        
        # Naviga fino al nodo del tool
        tool_node = tools_status.get("tools", {}).get(tool_key, {})
        
        # Recupera report_type per questo utente
        report_type_per_user = tool_node.get("report_type", {})
        
        if isinstance(report_type_per_user, dict) and user_id in report_type_per_user:
            user_value = report_type_per_user[user_id]
            
            # GESTIONE ARRAY: prendi il primo elemento valido
            if isinstance(user_value, list) and len(user_value) > 0:
                selected_type = user_value[0]
            # GESTIONE STRINGA DIRETTA (backward compatibility)
            elif isinstance(user_value, str):
                selected_type = user_value
            else:
                selected_type = None
            
            # Valida che il tipo sia supportato
            if selected_type and selected_type in get_valid_report_types():
                log.info(f"User '{user_id}' report type: {selected_type}")
                return selected_type
            else:
                log.warning(f"Invalid report type '{selected_type}' for user '{user_id}', using default")
        
        # Fallback al default
        config = load_report_types_config()
        default_type = config.get("default_report_type", "standard")
        log.info(f"Using default report type '{default_type}' for user '{user_id}'")
        return default_type
        
    except FileNotFoundError:
        log.error(f"File {TOOLS_STATUS_PATH} not found, using default report type")
        return "standard"
        
    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in {TOOLS_STATUS_PATH}: {e}, using default report type")
        return "standard"
        
    except Exception as e:
        log.error(f"Error loading user report type: {e}")
        return "standard"


# ===== TOOL PRINCIPALE =====

@tool(return_direct=True)
def create_report_in_word(tool_input: str, cat):
    """
    Creates a comprehensive Word report based on the conversation context and user request.
    
    Use this tool when the user explicitly asks to:
    - Create a report document
    - Generate a Word document
    - Export conversation/analysis to a document format
    - Summarize information in a document format
    
    Input should describe what to include in the report, for example:
    - "Create a report summarizing our conversation"
    - "Generate a technical document about the requirements discussed"
    - "Make a Word report with all the analysis results"
    - "Document our findings in a report"
    
    The tool will automatically gather information from:
    - Current conversation history
    - Declarative memories (retrieved documents)
    - Previous tool outputs
    - User's specific request
    """
    
    try:
        # ===== CARICA SETTINGS =====
        plugin_settings = cat.mad_hatter.get_plugin().load_settings()
        
        # plugin_settings è GIÀ un dizionario, non un oggetto Pydantic
        tool_key = plugin_settings.get("tool_name", "Report Maker")
        
        # Recupera user_id
        user_id = str(getattr(cat, "user_id", "admin") or "admin")
        
        # ===== LEGGE IL TIPO DI REPORT DA tools_status.json =====
        report_type = get_user_report_type(user_id, tool_key)
        
        log.info(f"Starting report generation - User: {user_id}, Type: {report_type}")
        
        # ===== FASE 1: RACCOLTA INFORMAZIONI =====
        cat.send_ws_message(
            f"Raccolta informazioni per generare il report ({report_type})...",
            msg_type="notification"
        )
        
        # Estrae informazioni dal contesto
        context_parts = []
        
        # 1. Messaggio corrente dell'utente
        user_message = cat.working_memory.user_message_json.text
        context_parts.append(f"## User's Request\n{user_message}")
        
        # 2. Storico conversazione
        chat_history = cat.working_memory.stringify_chat_history()
        if chat_history:
            context_parts.append(f"\n## Conversation History\n{chat_history}")
        
        # 3. Memorie dichiarative (documenti recuperati)
        if hasattr(cat.working_memory, 'declarative_memories') and cat.working_memory.declarative_memories:
            declarative_items = []
            for mem in cat.working_memory.declarative_memories[:5]:
                content = mem[0].page_content
                declarative_items.append(content)
            declarative_context = "\n\n".join(declarative_items)
            context_parts.append(f"\n## Retrieved Documents\n{declarative_context}")
        
        # 4. Output di tool precedenti
        if hasattr(cat.working_memory, 'agent_input') and hasattr(cat.working_memory.agent_input, 'tools_output'):
            tools_output = str(cat.working_memory.agent_input.tools_output)
            if tools_output:
                context_parts.append(f"\n## Previous Tools Output\n{tools_output}")
        
        # Costruisce il contesto completo
        full_context = "\n".join(context_parts)
        
        # ===== FASE 2: GENERAZIONE CONTENUTO MARKDOWN =====
        cat.send_ws_message(
            f"Generazione contenuto del report ({report_type})...",
            msg_type="notification"
        )
        
        log.info("Generating report content with LLM")
        
        # ===== USA IL TIPO DI REPORT PER SELEZIONARE IL PROMPT =====
        # plugin_settings è già un dizionario, passa direttamente
        report_generation_prompt = get_prompt_by_type(
            prompt_type=report_type,
            full_context=full_context,
            user_request=tool_input,
            settings=plugin_settings
        )
        
        # cat.send_ws_message(report_generation_prompt,"chat")
        # Genera il contenuto del report usando l'LLM
        markdown_content = cat.llm(report_generation_prompt)
        
        log.info(f"Report content generated ({len(markdown_content)} characters)")
        
        # ===== FASE 3: CARICAMENTO TEMPLATE E CONVERSIONE =====
        cat.send_ws_message(
            "Conversione in formato Word...",
            msg_type="notification"
        )
        
        log.info("Loading template and converting Markdown to Word document")
        
        # Carica il template
        doc = load_template_document(cat)
        
        # Converte Markdown in Word
        parse_markdown_to_word(doc, markdown_content)
        
        # ===== FASE 4: SALVATAGGIO FILE =====
        log.info("Saving Word document")
        
        # Genera nome file con timestamp e tipo di report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{user_id}_{report_type}_report_{timestamp}.docx"
        static_dir = _resolve_static_file("").resolve()
        static_dir.mkdir(parents=True, exist_ok=True)
        file_path = static_dir / filename

        doc.save(str(file_path))
        log.info(f"Document saved: {file_path}")
        download_url = f'{get_static_url()}{filename}?v={timestamp}'
        
        # Messaggio di risposta
        response_message = f"""**{report_type.replace('_', ' ').title()} Report created successfully!**

**File**: {filename}

**Download**: <a href="{download_url}" download>Click here to download your report</a>

**Content Summary**:
- Report type: {report_type.replace('_', ' ').title()}
- Generated from conversation context
- Template format.docx applied (header, footer, styles preserved)
- Includes analysis, findings, and recommendations
- Formatted as a professional Word document

The report has been saved and is ready for download."""

        # ===== FASE 6: NOTIFICA FINALE =====
        cat.send_ws_message(
            f"Report {report_type} generato: {filename}",
            msg_type="notification"
        )
        
        log.info("Report creation completed successfully")
        
        return response_message
        
    except Exception as e:
        # Usa traceback.format_exc() invece di exc_info=True
        error_traceback = traceback.format_exc()
        log.error(f"Error creating Word report: {e}\n{error_traceback}")
        
        return f"Error creating report: {str(e)}\n\nPlease try again or contact support if the issue persists."
