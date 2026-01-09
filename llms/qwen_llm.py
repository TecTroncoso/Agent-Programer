"""
QwenLLM - CrewAI BaseLLM wrapper for Qwen Chat client.
Uses the existing QwenChat project for actual API communication.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any, List, Union

from crewai import BaseLLM


def _load_qwen_modules():
    """Load QwenChat modules with unique names to avoid cache conflicts."""
    qwen_src = Path(__file__).parent.parent / "QwenChat" / "src"

    # Load config with unique name
    config_path = qwen_src / "config.py"
    config_spec = importlib.util.spec_from_file_location("qwen_src_config", config_path)
    config_module = importlib.util.module_from_spec(config_spec)
    sys.modules["qwen_src_config"] = config_module
    config_spec.loader.exec_module(config_module)

    # Load display with unique name
    display_path = qwen_src / "display.py"
    display_spec = importlib.util.spec_from_file_location(
        "qwen_src_display", display_path
    )
    display_module = importlib.util.module_from_spec(display_spec)
    sys.modules["qwen_src_display"] = display_module
    display_spec.loader.exec_module(display_module)

    # Now load client, but we need to patch its imports first
    client_path = qwen_src / "client.py"
    with open(client_path, "r", encoding="utf-8") as f:
        client_code = f.read()

    # Replace relative imports with our unique module names
    client_code = client_code.replace(
        "from .config import", "from qwen_src_config import"
    )
    client_code = client_code.replace(
        "from .display import", "from qwen_src_display import"
    )

    # Compile and execute
    client_module_name = "qwen_src_client"
    client_spec = importlib.util.spec_from_loader(client_module_name, loader=None)
    client_module = importlib.util.module_from_spec(client_spec)
    sys.modules[client_module_name] = client_module
    exec(compile(client_code, client_path, "exec"), client_module.__dict__)

    return client_module.QwenClient


# Cache the client class
_QwenClientClass = None


def _get_qwen_client_class():
    """Get the QwenClient class, loading it if necessary."""
    global _QwenClientClass
    if _QwenClientClass is None:
        _QwenClientClass = _load_qwen_modules()
    return _QwenClientClass


class QwenLLM(BaseLLM):
    """
    CrewAI LLM wrapper that uses Qwen (chat.qwen.ai) as backend.
    This is the ORCHESTRATOR model - good at planning and coordination.
    """

    def __init__(self, temperature: float = 0.7):
        super().__init__(model="qwen3-max-2025-10-30", temperature=temperature)
        self._client = None
        self._initialized = False

    def _ensure_client(self):
        """Lazy initialization of the Qwen client."""
        if not self._initialized:
            try:
                QwenClientClass = _get_qwen_client_class()
                self._client = QwenClientClass()
                self._initialized = True
            except Exception as e:
                raise RuntimeError(f"Failed to initialize QwenClient: {e}")

    def call(
        self,
        messages: Union[str, List[dict]],
        tools: List[dict] = None,
        callbacks: Any = None,
        available_functions: dict = None,
        **kwargs,
    ) -> str:
        """
        Process messages and return response from Qwen.
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
            return f"Error calling Qwen: {str(e)}"

    def supports_function_calling(self) -> bool:
        return False

    def supports_stop_words(self) -> bool:
        return False

    def get_context_window_size(self) -> int:
        return 32000
