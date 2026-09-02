# setup.py

from typing import Dict
from cat.mad_hatter.decorators import hook
from cat.log import log
from cat.looking_glass.stray_cat import StrayCat
import subprocess

# ---------------------- SETUP ----------------------

def run_crawl4ai_setup():
    try:
        subprocess.run(["crawl4ai-setup"], check=True)
        log.info("Crawl4AI setup completed successfully.")
        return "Crawl4AI setup completed successfully."
    except subprocess.CalledProcessError as e:
        log.error("Error during Crawl4AI setup:", e)
        return "Error during Crawl4AI setup."

@hook
def fast_reply(fast_reply: Dict, cat: StrayCat) -> Dict:
    user_message: str = cat.working_memory.user_message_json.text
    if user_message == "@setup crawl4ai-setup":
        result = run_crawl4ai_setup()
        fast_reply["output"] = result
        return fast_reply