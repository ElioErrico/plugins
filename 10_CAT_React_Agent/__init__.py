from cat.mad_hatter.decorators import hook
from cat.looking_glass.cheshire_cat import CheshireCat

from .agent import LangchainBaseAgent, ReActAgent

@hook
def plugin_factory_allowed_agents(agents, cat: CheshireCat) -> list[tuple[LangchainBaseAgent, str, str]]:
    agents.extend(
        [
            (ReActAgent, "REACT_AGENT", "ReAct Agent"),
        ]
    )
    return agents
