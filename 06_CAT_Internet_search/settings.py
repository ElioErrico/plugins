from pydantic import BaseModel
from cat.mad_hatter.decorators import plugin
from pydantic import BaseModel, Field, field_validator


class MySettings(BaseModel):
    tool_name: str = "Internet Search"
    duck_duck_go_search_description: str = Field(
        default="- Use 'duck_duck_go_search' for real-time or general information.\n"
    )
    crawl_site_content_description: str = Field(
        default="- Use 'crawl_site_content' to extract details from specified web pages.\n"
    )

@plugin
def settings_model():
    """
    Restituisce il modello Pydantic delle impostazioni.
    Il framework usa questo per validare e salvare i settings.
    """
    return MySettings
