from enum import Enum
from pydantic import BaseModel, Field, field_validator
from cat.mad_hatter.decorators import plugin


class Languages(Enum):
    English = "English"
    French = "French"
    German = "German"
    Italian = "Italian"
    Spanish = "Spanish"
    Russian = "Russian"
    Chinese = "Chinese"
    Japanese = "Japanese"
    Korean = "Korean"
    NoLanguage = "None"
    Human = "Human"

def validate_threshold(value):
    if value <= 0:
        return False
    return True

class MySettings(BaseModel):
    # Prompt prefix incipit
    prompt_prefix_incipit: str = Field(
        title="Prompt Prefix Incipit",
        default="You are an advanced AI assistant capable of complex reasoning and tool utilization. Your goal is to solve problems systematically by breaking them down into manageable steps and leveraging available tools when necessary.\n\n## Core Reasoning Process\n\nWhen approaching any problem:\n1. **Understand**: Carefully analyze what is being asked. Identify key requirements, constraints, and desired outcomes.\n2. **Decompose**: Break complex problems into smaller, manageable sub-problems. Identify dependencies and logical sequences.\n3. **Plan**: Develop a clear strategy before acting. Consider what information you need and which tools can provide it.\n4. **Execute**: Take actions methodically, one step at a time. Each action should build upon previous results.\n5. **Verify**: After each step, evaluate if the result meets expectations. Adjust your approach if needed.\n6. **Synthesize**: Combine all gathered information into a coherent, comprehensive answer.\n\n",
        extra={"type": "TextArea"},
    )

    # Prompt sections
    tool_orchestration_header: str = Field(
        title="Tool Orchestration Header",
        default="## Tool Usage Guidelines\n",
        extra={"type": "TextArea"},
    )    

    episodic_memory_k: int = 3
    episodic_memory_threshold: float = 0.7
    declarative_memory_k: int = 3
    declarative_memory_threshold: float = 0.7
    procedural_memory_k: int = 3
    procedural_memory_threshold: float = 0.7
    user_name: str | None = "Human"
    language: Languages = Languages.English
    chunk_size: int = 256
    chunk_overlap: int = 64

    @field_validator("episodic_memory_threshold")
    @classmethod
    def episodic_memory_threshold_validator(cls, threshold):
        if not validate_threshold(threshold):
            raise ValueError("Episodic memory threshold must be greater than 1")

    @field_validator("declarative_memory_threshold")
    @classmethod
    def declarative_memory_threshold_validator(cls, threshold):
        if not validate_threshold(threshold):
            raise ValueError("Declarative memory threshold must be greater than 1")

    @field_validator("procedural_memory_threshold")
    @classmethod
    def procedural_memory_threshold_validator(cls, threshold):
        if not validate_threshold(threshold):
            raise ValueError("Procedural memory threshold must be greater than 1")


@plugin
def settings_model():
    """
    Restituisce il modello Pydantic delle impostazioni del plugin.
    Serve al framework per esporre schema e persistenza dei settings.
    """
    return MySettings



