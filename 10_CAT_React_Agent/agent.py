import time
from typing import List
from datetime import timedelta

from cat.convo.messages import CatMessage
from cat.looking_glass.stray_cat import StrayCat
from cat.plugins.agent_factory import LangchainBaseAgent, AgentOutput, LLMAction
from cat.utils import verbal_timedelta

from .settings import Settings


class ReActAgent(LangchainBaseAgent):

    def __init__(self):
        super().__init__()

    def execute(self, cat: StrayCat) -> AgentOutput:
        # If a form is active, handle it and return the result
        if res := self.handle_active_form(cat):
            return res

        unprocessed_actions: List[LLMAction] = []
        max_iterations = Settings.load_setting(cat).max_iterations

        for _ in range(max_iterations):
            response = self._get_response(cat)
            actions = response.actions
            output_text = response.output or ""
    
            # Stop the agent if no new actions are produced
            if not actions:
                return AgentOutput(
                    output=output_text,
                    actions=unprocessed_actions,
                )

            if output_text:
                msg = AgentOutput(
                    output=output_text,
                    actions=[action for action in actions if action.return_direct],
                )
                self._send_direct_message(msg, cat=cat)

            args = {
                "cat": cat,
                "actions": actions,
                "unprocessed_actions": unprocessed_actions,
            }
            if final_mesage := self._execute_and_dispatch_actions(**args):
                return final_mesage
                        
        return AgentOutput(
            output="Maximum agent iterations reached write `continue` to continue.",
            actions=unprocessed_actions,
        )
       
    def _get_response(self, cat: StrayCat) -> AgentOutput:
        # Using the hook `agent_allowed_tools` to better integrate
        # the agent with the rest of the system
        allowed_procedures_names = cat.mad_hatter.execute_hook(
            "agent_allowed_tools",
            self.get_recalled_procedures_names(cat),
            cat=cat,
        )
        allowed_procedures = self.get_procedures(allowed_procedures_names)

        return self.run_chain(
            cat=cat,
            system_prompt=self._get_prompt(cat),
            procedures=allowed_procedures,
            max_procedures_calls=Settings.load_setting(cat).max_procedures_calls,
            execute_procedures=False,
            chain_name="Simple Agent",
        )

    def _execute_and_dispatch_actions(
        self,
        actions: List[LLMAction],
        cat: StrayCat,
        unprocessed_actions: List[LLMAction] = [],
    ) -> AgentOutput | None:
        
        last_action = None
        if all(action.return_direct for action in actions):
            last_action = actions.pop()

        for action in actions:
            executed_action = self.execute_action(action, cat=cat)
            if not executed_action.return_direct:
                # If the action is not a direct message, store it for later use
                unprocessed_actions.append(executed_action)
                self.save_action(executed_action, cat=cat)
                continue

            # If the action is a direct message, send it immediately
            self._send_direct_message(
                AgentOutput(
                    output=executed_action.output,
                    actions=[executed_action],
                ), cat=cat,
            )

        if last_action:
            executed_action = self.execute_action(last_action, cat=cat)
            return AgentOutput( 
                output=executed_action.output,
                actions=[executed_action],
            )

        return None
        
    def _get_prompt(self, cat: StrayCat) -> str:
        system_prompt = cat.mad_hatter.execute_hook(
            "agent_prompt_prefix",
            "",
            cat=cat,
        )

        if episodic_memories := self.get_recalled_episodic_memory(cat):
            current_time = time.time()
            formatted_episodic_memories = "\n".join(
                f" - {content} ({verbal_timedelta(timedelta(seconds=(current_time - metadata['when'])))})"
                for content, metadata in episodic_memories
            )
            system_prompt += f"\n\nThings the user said:\n{formatted_episodic_memories}"

        if declarative_memories :=  self.get_recalled_declarative_memory(cat):
            formatted_declarative_memories = "".join(
                f" - {content} (from {metadata['source']})"
                for content, metadata in declarative_memories
            )
            system_prompt += f"\n\nDeclarative Memories:\n{formatted_declarative_memories}"

        return system_prompt

    @staticmethod
    def _send_direct_message(result: AgentOutput, cat: StrayCat) -> CatMessage:
        # Build the message metadata
        why = cat._StrayCat__build_why()
        why.intermediate_steps = result.intermediate_steps

        # Send the message to the chat and save it in the chat history
        cat.send_chat_message(
            CatMessage(user_id=cat.user_id, text=result.output, why=why),
            save=True,
        )
