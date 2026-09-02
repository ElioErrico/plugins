from cat.mad_hatter.decorators import plugin
from pydantic import BaseModel, Field, field_validator

class Settings(BaseModel):
    """
    Settings for the React Agent plugin.
    """
    max_iterations: int = Field(
        default=5,
        description="Maximum number of iterations to run the agent.",
    )
    max_procedures_calls: int = Field(
        default=10,
        description="Maximum number of procedure calls allowed per iteration.",
    )

    @field_validator("max_iterations", "max_procedures_calls")
    def validate_positive(cls, value):
        if value <= 0:
            raise ValueError("Value must be a positive integer.")
        return value
   
    @staticmethod
    def load_setting(cat) -> "Settings":
        """
        Load the settings from the plugin's configuration.
        """
        return Settings(**cat.mad_hatter.get_plugin().load_settings())

@plugin
def settings_model() -> Settings:
    """
    Returns the settings for the React Agent plugin.
    """
    return Settings
