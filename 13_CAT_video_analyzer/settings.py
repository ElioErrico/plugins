from pydantic import BaseModel, Field

from cat.mad_hatter.decorators import plugin


class VideoAnalyzerSettings(BaseModel):
    tool_name: str = Field(
        default="video_analyzer",
        description="Nome logico del tool esposto dal plugin.",
    )
    video_analyzer_description: str = Field(
        default="- Use 'video_analyzer' to analyze videos and get a structured result.\n",
        description="Descrizione prompt del tool video_analyzer.",
    )
    remember_tool_name: str = Field(
        default="ricorda il video: ...il video...",
        description="Nome logico usato dal comando fast_reply per memorizzare un'analisi video.",
    )
    backend_base_url: str = Field(
        default="http://host.docker.internal:8000",
        description="URL base del backend Video Analyzer raggiungibile dal container Cheshire Cat.",
    )
    client: str = Field(
        default="openai_api",
        description="Client LLM da inviare al backend Video Analyzer.",
    )
    api_key: str = Field(
        default="...",
        description="API key del provider LLM da inviare al backend Video Analyzer.",
    )
    api_url: str = Field(
        default="https://api.openai.com/v1",
        description="API base URL del provider LLM usato dal backend Video Analyzer.",
    )
    model: str = Field(
        default="gpt-4o",
        description="Modello LLM da usare per l'analisi video.",
    )
    keep_frames: bool = Field(
        default=True,
        description="Se true, chiede al backend di mantenere i frame estratti.",
    )


@plugin
def settings_model():
    return VideoAnalyzerSettings
