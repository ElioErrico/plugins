from pydantic import BaseModel
from cat.mad_hatter.decorators import plugin
from pydantic import BaseModel, Field, field_validator


class MySettings(BaseModel):
    tool_name: str = "Approfondisci documentazione"
    declarative_search_description: str = Field(
        default="- Use 'declarative_search' for iterative documentation research, using it at least 3 times to deepen understanding when needed."
    )

@plugin
def settings_model():
    """
    Restituisce il modello Pydantic delle impostazioni.
    Il framework usa questo per validare e salvare i settings.
    """
    return MySettings
