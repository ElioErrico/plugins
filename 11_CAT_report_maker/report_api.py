"""
API endpoint per esporre metadata del Report Maker.
Fornisce la lista dei tipi di report disponibili dal file report_types_config.json
"""

from cat.mad_hatter.decorators import endpoint
from fastapi import HTTPException
from cat.log import log
import json
import os

# ===== PERCORSI =====
try:
    # Percorso del plugin (dove si trova questo file)
    PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
    REPORT_TYPES_CONFIG_PATH = os.path.join(PLUGIN_DIR, "report_types_config.json")
    
    log.info(f"Report API - Plugin dir: {PLUGIN_DIR}")
    log.info(f"Report API - Config path: {REPORT_TYPES_CONFIG_PATH}")
    
except Exception as e:
    log.error(f"Errore nel calcolo dei percorsi per Report API: {str(e)}")
    raise


# ===== GET /report-maker/metadata =====
@endpoint.get("/report-maker/metadata")
def get_report_maker_metadata():
    """
    Restituisce i metadata per configurare il Report Maker.
    
    Returns:
        {
            "success": true,
            "tool_key": "Report Maker",
            "settings": {
                "report_type": {
                    "type": "enum",
                    "label": "Report Type",
                    "description": "Select the type of report to generate",
                    "options": [
                        {
                            "value": "standard",
                            "label": "📄 Standard Report",
                            "description": "General purpose report..."
                        },
                        ...
                    ],
                    "default": "standard"
                }
            },
            "version": "1.0.0"
        }
    
    Raises:
        HTTPException: 404 se il file config non esiste
        HTTPException: 500 se il JSON non è valido o altro errore
    """
    try:
        # Verifica esistenza file
        if not os.path.exists(REPORT_TYPES_CONFIG_PATH):
            log.error(f"File config non trovato: {REPORT_TYPES_CONFIG_PATH}")
            raise HTTPException(
                status_code=404,
                detail=f"File report_types_config.json non trovato"
            )
        
        # Carica configurazione
        with open(REPORT_TYPES_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Estrai report types
        report_types = config.get("report_types", [])
        default_type = config.get("default_report_type", "standard")
        version = config.get("version", "1.0.0")
        
        # Valida che ci sia almeno un tipo
        if not report_types:
            log.warning("Nessun report type trovato nel config")
            raise HTTPException(
                status_code=500,
                detail="Configurazione report types vuota o non valida"
            )
        
        # Trasforma in formato per frontend
        options = []
        for rt in report_types:
            # Valida campi obbligatori
            if "key" not in rt or "label" not in rt:
                log.warning(f"Report type invalido (manca key o label): {rt}")
                continue
            
            options.append({
                "value": rt["key"],
                "label": rt["label"],
                "description": rt.get("description", ""),
                "emoji": rt.get("emoji", "")
            })
        
        # Risposta strutturata
        response = {
            "success": True,
            "tool_key": "Report Maker",
            "settings": {
                "report_type": {
                    "type": "enum",
                    "label": "Report Type",
                    "description": "Select the type of report to generate",
                    "options": options,
                    "default": default_type
                }
            },
            "version": version
        }
        
        log.info(f"Report metadata loaded successfully: {len(options)} types available")
        return response
        
    except FileNotFoundError:
        log.error(f"File non trovato: {REPORT_TYPES_CONFIG_PATH}")
        raise HTTPException(
            status_code=404,
            detail="File report_types_config.json non trovato"
        )
        
    except json.JSONDecodeError as e:
        log.error(f"JSON non valido in report_types_config.json: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"JSON non valido in report_types_config.json: {str(e)}"
        )
        
    except HTTPException:
        # Re-raise HTTPException senza wrapping
        raise
        
    except Exception as e:
        log.error(f"Errore imprevisto nel caricamento metadata: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel caricamento metadata: {str(e)}"
        )

