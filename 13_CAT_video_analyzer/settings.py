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
        default="__FROM_ENV__",
        description="API key del provider LLM; lascia __FROM_ENV__ per leggerla da VIDEO_ANALYZER_API_KEY o OPENAI_API_KEY.",
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
    transcription_execution_mode: str = Field(
        default="openai",
        description="Modalita di trascrizione audio del backend: 'local' oppure 'openai'.",
    )
    transcription_local_model: str = Field(
        default="medium",
        description="Modello locale usato dal backend quando transcription_execution_mode='local'.",
    )
    transcription_openai_model: str = Field(
        default="gpt-4o-mini-transcribe",
        description="Modello OpenAI usato dal backend quando transcription_execution_mode='openai'.",
    )
    transcription_api_key: str = Field(
        default="__FROM_ENV__",
        description="API key per la trascrizione OpenAI; lascia __FROM_ENV__ per leggere VIDEO_ANALYZER_TRANSCRIPTION_API_KEY o OPENAI_API_KEY.",
    )
    transcription_api_url: str = Field(
        default="https://api.openai.com/v1",
        description="API base URL per la trascrizione OpenAI del backend.",
    )
    transcription_language: str = Field(
        default="it",
        description="Codice lingua ISO da suggerire alla trascrizione audio.",
    )
    transcription_device: str = Field(
        default="cpu",
        description="Device usato dalla trascrizione locale del backend.",
    )
    transcription_timeout: float = Field(
        default=300.0,
        description="Timeout in secondi per la richiesta di trascrizione OpenAI.",
    )
    transcription_prompt: str = Field(
        default="",
        description="Prompt opzionale da inviare al motore di trascrizione.",
    )


@plugin
def settings_model():
    return VideoAnalyzerSettings
