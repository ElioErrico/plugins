# cat/plugins/CAT_doc_front_end_manager/settings.py

from pydantic import BaseModel, Field
from cat.mad_hatter.decorators import plugin
from cat.log import log
from .filter_and_upload import aggiorna_users_tags


class MySettings(BaseModel):
    # Impostazione di esempio (potrai usarla altrove nel plugin se serve)
    add_new_users: bool = Field(
        False,
        description=(
            "Se true, il sistema può aggiungere automaticamente nuovi utenti al file user_status.json "
            "quando vengono rilevati (logica applicativa da gestire altrove)."
        ),
    )


@plugin
def settings_schema():
    """
    Espone lo schema delle impostazioni del plugin.
    In più, allinea lo schema di user_status.json con i tag correnti (senza rimuovere nulla),
    sostituendo la vecchia chiamata a 'aggiorna_users_tags_solo_nuovi'.
    """
    try:
        aggiorna_users_tags()
    except Exception as e:
        # Non bloccare l'esposizione dello schema in caso di problemi di sync
        log.error(f"[settings_schema] aggiorna_users_tags() failed: {e}")

    # Pydantic v2: usare model_json_schema() (schema() è deprecato)
    return MySettings.model_json_schema()
