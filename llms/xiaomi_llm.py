"""
XiaomiLLM - CrewAI BaseLLM wrapper for Xiaomi AI Studio client.
Uses the existing ChatXiaomi project for actual API communication.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any, List, Union

from crewai import BaseLLM


def _load_xiaomi_modules():
    """Load ChatXiaomi modules with unique names to avoid cache conflicts."""
    xiaomi_src = Path(__file__).parent.parent / "ChatXiaomi" / "src"

    # Load config with unique name
    config_path = xiaomi_src / "config.py"
    config_spec = importlib.util.spec_from_file_location(
        "xiaomi_src_config", config_path
    )
    config_module = importlib.util.module_from_spec(config_spec)
    sys.modules["xiaomi_src_config"] = config_module
    config_spec.loader.exec_module(config_module)

    # Load display with unique name
    display_path = xiaomi_src / "display.py"
    display_spec = importlib.util.spec_from_file_location(
        "xiaomi_src_display", display_path
    )
    display_module = importlib.util.module_from_spec(display_spec)
    sys.modules["xiaomi_src_display"] = display_module
    display_spec.loader.exec_module(display_module)

    # Now load client, but we need to patch its imports first
    client_path = xiaomi_src / "client.py"
    with open(client_path, "r", encoding="utf-8") as f:
        client_code = f.read()

    # Replace relative imports with our unique module names
    client_code = client_code.replace(
        "from .config import", "from xiaomi_src_config import"
    )
    client_code = client_code.replace(
        "from .display import", "from xiaomi_src_display import"
    )

    # Compile and execute
    client_module_name = "xiaomi_src_client"
    client_spec = importlib.util.spec_from_loader(client_module_name, loader=None)
    client_module = importlib.util.module_from_spec(client_spec)
    sys.modules[client_module_name] = client_module
    exec(compile(client_code, client_path, "exec"), client_module.__dict__)

    return client_module.KimiClient


# Cache the client class
_KimiClientClass = None


def _get_xiaomi_client_class():
    """Get the KimiClient class, loading it if necessary."""
    global _KimiClientClass
    if _KimiClientClass is None:
        _KimiClientClass = _load_xiaomi_modules()
    return _KimiClientClass


class XiaomiLLM(BaseLLM):
    """
    CrewAI LLM wrapper that uses Xiaomi AI Studio (mimo-v2-flash-studio) as backend.
    This is the PROGRAMMER model - specialized in code generation.
    """

    def __init__(self, temperature: float = 0.8):
        super().__init__(model="mimo-v2-flash-studio", temperature=temperature)
        self._client = None
        self._initialized = False

    def _ensure_client(self):
        """Lazy initialization of the Xiaomi client."""
        if not self._initialized:
            try:
                KimiClientClass = _get_xiaomi_client_class()
                self._client = KimiClientClass()
                self._initialized = True
            except Exception as e:
                raise RuntimeError(f"Failed to initialize KimiClient (Xiaomi): {e}")

    def call(
        self,
        messages: Union[str, List[dict]],
        tools: List[dict] = None,
        callbacks: Any = None,
        available_functions: dict = None,
        **kwargs,
    ) -> str:
        """
        Process messages and return response from Xiaomi AI Studio.
        """
        self._ensure_client()

        # Extract the prompt from messages
        if isinstance(messages, str):
            prompt = messages
            system_prompt = None
        else:
            system_prompt = None
            prompt = ""

            for msg in messages:
                role = msg.get("role", "")
                content = msg.get("content", "")

                if role == "system":
                    system_prompt = content
                elif role == "user":
                    prompt = content

            if not prompt and messages:
                prompt = messages[-1].get("content", "")

        try:
            response = self._client.send_message(prompt, system_prompt=system_prompt)
            return response if response else "No response received"
        except Exception as e:
            return f"Error calling Xiaomi: {str(e)}"

    def supports_function_calling(self) -> bool:
        return False

    def supports_stop_words(self) -> bool:
        return False

    def get_context_window_size(self) -> int:
        return 32000
