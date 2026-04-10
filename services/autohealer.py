import traceback
import sys
import httpx
import logging
from config.settings import Settings

logger = logging.getLogger(__name__)

class JulesAutoHealer:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_key = settings.jules_api_key
        # Temporary fallback placeholder for whatever Jules API URL is needed
        self.endpoint = "https://api.jules.ai/v1/autoheal"

    async def analyze_crash(self, exception: Exception, context_hint: str = "") -> str:
        """
        Takes an exception, formats the stack trace, and sends it to the Jules API
        to generate an autonomous root cause analysis or hot-patch.
        """
        # If doppler hasn't populated a real key yet, skip processing
        if not self.api_key or self.api_key == "sk_jules_placeholder":
            logger.warning("Jules API key not configured in Doppler. Skipping autoheal analysis.")
            return "Autohealer Disabled: Missing Jules API Key in Doppler."

        # Extract full trace from the passed exception
        if exception:
            exc_type = type(exception)
            exc_value = exception
            exc_traceback = exception.__traceback__
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            stack_trace = "".join(tb_lines)
            exc_name = exc_type.__name__
        else:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
            stack_trace = "".join(tb_lines)
            exc_name = exc_type.__name__ if exc_type else "UnknownException"

        logger.info(f"Sending crash report to Jules Autohealer: {exc_name}")
        
        prompt = (
            f"An error occurred in the ClipFLOW pipeline.\n"
            f"Context: {context_hint}\n"
            f"Exception Stack Trace:\n"
            f"```python\n{stack_trace}\n```\n"
            f"Please provide a root cause analysis and a Python patch to fix this issue."
        )

        try:
            # Send payload to the Jules API endpoint
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"prompt": prompt, "codebase": "ClipFLOW"},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                analysis = data.get("fix", "No fix provided by Jules.")
                
                logger.error(f"🚨 JULES AUTOHEALER PROPOSED FIX 🚨\n{analysis}\n{'='*50}")
                return analysis

        except Exception as e:
            logger.error(f"Failed to communicate with Jules API: {str(e)}")
            return f"Autohealer API connection failed: {str(e)}"
