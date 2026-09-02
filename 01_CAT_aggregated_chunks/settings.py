from pydantic import BaseModel
from cat.mad_hatter.decorators import plugin
from pydantic import BaseModel, Field, field_validator


class MySettings(BaseModel):
    n_of_chunks: int = 5
    enable_classification: bool = True  # New setting to enable/disable classification

@plugin
def settings_model():
    """
    Restituisce il modello Pydantic delle impostazioni.
    Il framework usa questo per validare e salvare i settings.
    """
    return MySettings
    
