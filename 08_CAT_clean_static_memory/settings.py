from pydantic import BaseModel, Field, field_validator
from cat.mad_hatter.decorators import plugin


class MySettings(BaseModel):
    cleanup_hour: int = Field(
        default=17,
        ge=0,
        le=23,
        description="Ora del giorno per la pulizia automatica della cartella static (0-23)"
    )
    
    cleanup_minute: int = Field(
        default=16,
        ge=0,
        le=59,
        description="Minuto dell'ora per la pulizia automatica (0-59)"
    )
    
    timezone: str = Field(
        default="Europe/Rome",
        description="Fuso orario locale per la schedulazione (es. Europe/Rome, America/New_York, Asia/Tokyo)"
    )


@plugin
def settings_model():
    """
    Restituisce il modello Pydantic delle impostazioni.
    Il framework usa questo per validare e salvare i settings.
    """
    return MySettings