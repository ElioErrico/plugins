"""
Plugin per la pulizia automatica della cartella static
Elimina giornalmente tutti i file tranne quelli .json all'orario configurato

Nota: Il job viene schedulato quando i settings vengono salvati.

IMPORTANTE: Lo scheduler usa UTC, quindi l'orario viene convertito automaticamente.
"""

from cat.mad_hatter.decorators import hook
from cat.log import log
import os
import shutil
from pathlib import Path
from datetime import datetime
import pytz

def cleanup_static_folder(cat):
    """
    Elimina file e cartelle nella cartella static, preservando i file .json
    e i file il cui nome inizia con "format"
    
    Parameters
    ----------
    cat : CheshireCat o StrayCat
        Istanza del Cat per accedere ai servizi (es. invio messaggi WebSocket)
    """
    try:
        # Ottieni il percorso della cartella static
        root_dir = os.environ.get("CCAT_ROOT", os.getcwd())
        static_dir = Path(root_dir) / "cat" / "static"
        
        if not static_dir.exists():
            log.warning(f"[Static Cleanup] Cartella {static_dir} non trovata")
            return
        
        deleted_files = []
        preserved_files = []
        errors = []
        
        # Log inizio operazione con timestamp
        now = datetime.now()
        log.info(f"[Static Cleanup] Avvio pulizia alle {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Itera su tutti i file nella cartella static
        for file_path in static_dir.iterdir():
            if file_path.is_dir():
                try:
                    shutil.rmtree(file_path)
                    deleted_files.append(f"{file_path.name}/")
                    log.info(f"[Static Cleanup] Cartella eliminata: {file_path.name}")
                except Exception as e:
                    errors.append(f"{file_path.name}/: {str(e)}")
                    log.error(f"[Static Cleanup] Errore eliminazione cartella {file_path.name}: {e}")
                continue
            
            # Preserva i file .json
            if file_path.suffix.lower() == '.json':
                preserved_files.append(file_path.name)
                log.debug(f"[Static Cleanup] Preservato: {file_path.name}")
                continue

            # Preserva i file il cui nome inizia con "format"
            if file_path.name.startswith('format'):
                preserved_files.append(file_path.name)
                log.debug(f"[Static Cleanup] Preservato (inizia con 'format'): {file_path.name}")
                continue  
                      
            # Elimina tutti gli altri file
            try:
                file_path.unlink()
                deleted_files.append(file_path.name)
                log.info(f"[Static Cleanup] Eliminato: {file_path.name}")
            except Exception as e:
                errors.append(f"{file_path.name}: {str(e)}")
                log.error(f"[Static Cleanup] Errore eliminazione {file_path.name}: {e}")
        
        # Log riepilogo
        summary = (
            f"[Static Cleanup] Completato - "
            f"Eliminati: {len(deleted_files)}, "
            f"Preservati: {len(preserved_files)}, "
            f"Errori: {len(errors)}"
        )
        log.info(summary)
        
    except Exception as e:
        log.error(f"[Static Cleanup] Errore critico durante la pulizia: {e}")


def schedule_cleanup_job(cat, settings):
    """
    Schedula il job di pulizia con le impostazioni fornite.
    Rimuove il job esistente e ne crea uno nuovo con i nuovi parametri.
    
    Parameters
    ----------
    cat : CheshireCat
        Istanza del Cheshire Cat
    settings : dict
        Dizionario con le impostazioni (cleanup_hour, cleanup_minute, timezone)
    """
    job_id = "daily_static_cleanup"
    
    # Estrai le impostazioni
    cleanup_hour = settings.get("cleanup_hour", 17)
    cleanup_minute = settings.get("cleanup_minute", 16)
    timezone_str = settings.get("timezone", "Europe/Rome")
    
    log.info(f"[Static Cleanup] Schedulazione job con: {cleanup_hour}:{cleanup_minute:02d} ({timezone_str})")
    
    # Rimuovi il job esistente se presente
    existing_job = cat.white_rabbit.get_job(job_id)
    if existing_job:
        cat.white_rabbit.remove_job(job_id)
        log.info(f"[Static Cleanup] Job esistente '{job_id}' rimosso per ri-schedulazione")
    
    # Converti l'orario locale in UTC
    try:
        local_tz = pytz.timezone(timezone_str)
        log.debug(f"[Static Cleanup] Timezone '{timezone_str}' caricato correttamente")
    except Exception as e:
        log.error(f"[Static Cleanup] Timezone '{timezone_str}' non valido: {e}. Uso 'Europe/Rome'")
        local_tz = pytz.timezone('Europe/Rome')
        timezone_str = 'Europe/Rome'
    
    # Crea un datetime per l'orario configurato
    now = datetime.now(local_tz)
    target_time_local = now.replace(
        hour=cleanup_hour, 
        minute=cleanup_minute, 
        second=0, 
        microsecond=0
    )
    
    # Converti in UTC
    target_time_utc = target_time_local.astimezone(pytz.utc)
    
    utc_hour = target_time_utc.hour
    utc_minute = target_time_utc.minute
    
    # Schedula il job giornaliero con l'orario UTC
    try:
        cat.white_rabbit.schedule_cron_job(
            cleanup_static_folder,
            job_id=job_id,
            hour=utc_hour,
            minute=utc_minute,
            cat=cat  # Passa l'istanza del Cat alla funzione schedulata
        )
        
        log.info(f"[Static Cleanup] ✅ Job '{job_id}' schedulato con successo")
        log.info(f"[Static Cleanup] ⏰ Orario configurato: {cleanup_hour:02d}:{cleanup_minute:02d} ({timezone_str})")
        log.info(f"[Static Cleanup] 🌍 Orario UTC: {utc_hour:02d}:{utc_minute:02d}")
        
        # Verifica il job appena creato
        created_job = cat.white_rabbit.get_job(job_id)
        if created_job:
            next_run = created_job.get('next_run')
            log.info(f"[Static Cleanup] 📅 Prossima esecuzione: {next_run}")
        
    except Exception as e:
        log.error(f"[Static Cleanup] ❌ Errore durante la schedulazione del job: {e}")

@hook
def fast_reply(fast_reply: dict, cat):
    user_message = (cat.working_memory.user_message_json.text or "").strip()

    if user_message == "update_static_cleanup_time":
        try:
            settings = cat.mad_hatter.get_plugin().load_settings() or {}
            schedule_cleanup_job(cat, settings)

            cleanup_hour = settings.get("cleanup_hour", 17)
            cleanup_minute = settings.get("cleanup_minute", 16)
            timezone_str = settings.get("timezone", "Europe/Rome")
            fast_reply["output"] = (
                "[Static Cleanup] Timing aggiornato: "
                f"{cleanup_hour:02d}:{cleanup_minute:02d} ({timezone_str})."
            )
        except Exception as e:
            log.error(f"[Static Cleanup] Errore durante l'aggiornamento timing: {e}")
            fast_reply["output"] = (
                "[Static Cleanup] Errore durante l'aggiornamento timing: "
                f"{e}"
            )
        return fast_reply

    if user_message == "clean_static_now":
        try:
            cleanup_static_folder(cat)
            fast_reply["output"] = "[Static Cleanup] Pulizia della cartella static eseguita ora."
        except Exception as e:
            log.error(f"[Static Cleanup] Errore durante la pulizia manuale: {e}")
            fast_reply["output"] = (
                "[Static Cleanup] Errore durante la pulizia manuale: "
                f"{e}"
            )
        return fast_reply

    return fast_reply
    
