import json
import uuid
import time
import httpx
from .config import Config
from .display import print_status, print_response_start, stream_live, stream_thinking


class QwenClient:
    def __init__(self):
        self.config = Config()
        self.cookies = self._load_cookies()
        self.token = self._get_token_from_cookies()
        self.conversation_id = None
        self.parent_id = None
        self.thinking_enabled = False  # Toggle for thinking mode
        self.thinking_budget = 81920  # Default thinking budget
        self.client = httpx.Client(timeout=120.0)

    def _load_cookies(self):
        try:
            with open(self.config.COOKIES_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def _get_token_from_cookies(self):
        """Extract token from cookies - Qwen stores it there"""
        if "token" in self.cookies:
            return self.cookies["token"]
        try:
            with open(self.config.TOKEN_FILE, "r") as f:
                return f.read().strip()
        except FileNotFoundError:
            return None

    def _get_headers(self):
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": self.config.BASE_URL,
            "Referer": f"{self.config.BASE_URL}/",
            "User-Agent": self.config.BASE_HEADERS["User-Agent"],
            "X-Request-Id": str(uuid.uuid4()),
            "X-Accel-Buffering": "no",
            "source": "web",
        }

    def _create_conversation(self):
        """Create a new chat conversation using Qwen API"""
        if self.conversation_id:
            return self.conversation_id

        headers = self._get_headers()

        payload = {
            "title": "New Chat",
            "models": ["qwen3-max-2025-10-30"],
            "chat_mode": "normal",
            "chat_type": "t2t",
            "timestamp": int(time.time() * 1000),
            "project_id": "",
        }

        try:
            resp = self.client.post(
                f"{self.config.BASE_URL}/api/v2/chats/new",
                headers=headers,
                cookies=self.cookies,
                json=payload,
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("data", {}).get("id"):
                    self.conversation_id = data["data"]["id"]
                    print_status(
                        f"Created conversation: {self.conversation_id[:8]}...", "green"
                    )
                    return self.conversation_id

            print_status(f"Failed to create conversation: {resp.status_code}", "red")
            print_status(f"Response: {resp.text[:200]}", "yellow")
            return None

        except Exception as e:
            print_status(f"Error creating conversation: {e}", "red")
            return None

    def enable_thinking(self, enabled=True, budget=81920):
        """Enable or disable thinking mode"""
        self.thinking_enabled = enabled
        self.thinking_budget = budget
        status = "enabled" if enabled else "disabled"
        print_status(f"Thinking mode {status} (budget: {budget})", "cyan")

    def chat(self, prompt):
        if not self.cookies:
            print_status("No cookies found - please login first", "red")
            return

        if not self.conversation_id:
            print_status("Creating chat session...", "cyan")
            if not self._create_conversation():
                print_status("Failed to create session", "red")
                return

        print_status("Sending message...", "cyan")

        headers = self._get_headers()

        message_fid = str(uuid.uuid4())
        child_id = str(uuid.uuid4())
        current_timestamp = int(time.time())

        # Build feature_config with thinking support
        feature_config = {
            "thinking_enabled": self.thinking_enabled,
            "output_schema": "phase",
            "research_mode": "normal",
        }

        if self.thinking_enabled:
            feature_config["thinking_budget"] = self.thinking_budget

        payload = {
            "stream": True,
            "version": "2.1",
            "incremental_output": True,
            "chat_id": self.conversation_id,
            "chat_mode": "normal",
            "model": "qwen3-max-2025-10-30",
            "parent_id": self.parent_id,
            "messages": [
                {
                    "fid": message_fid,
                    "parentId": self.parent_id,
                    "childrenIds": [child_id],
                    "role": "user",
                    "content": prompt,
                    "user_action": "chat",
                    "files": [],
                    "timestamp": current_timestamp,
                    "models": ["qwen3-max-2025-10-30"],
                    "chat_type": "t2t",
                    "feature_config": feature_config,
                    "extra": {"meta": {"subChatType": "t2t"}},
                    "sub_chat_type": "t2t",
                    "parent_id": self.parent_id,
                }
            ],
            "timestamp": current_timestamp,
        }

        try:
            with self.client.stream(
                "POST",
                f"{self.config.BASE_URL}/api/v2/chat/completions?chat_id={self.conversation_id}",
                headers=headers,
                cookies=self.cookies,
                json=payload,
            ) as resp:
                if resp.status_code != 200:
                    print_status(f"Request failed: {resp.status_code}", "red")
                    try:
                        error_text = resp.read().decode()
                        print_status(f"Error: {error_text[:300]}", "red")
                    except:
                        pass
                    return

                thinking_content = ""
                answer_content = ""
                current_phase = None

                for line in resp.iter_lines():
                    if not line:
                        continue

                    if line.startswith("data:"):
                        json_str = line[5:].strip()
                        if not json_str or json_str == "[DONE]":
                            continue

                        try:
                            data = json.loads(json_str)

                            # Handle response.created event - get response_id for threading
                            if "response.created" in data:
                                created_info = data["response.created"]
                                # Use response_id as the parent for next message
                                if "response_id" in created_info:
                                    self.parent_id = created_info["response_id"]
                                continue

                            # Handle content streaming
                            if "choices" in data:
                                for choice in data["choices"]:
                                    delta = choice.get("delta", {})
                                    content = delta.get("content", "")
                                    phase = delta.get("phase", "answer")
                                    status = delta.get("status", "")

                                    # Phase changed - display accumulated content
                                    if phase != current_phase:
                                        if (
                                            current_phase == "think"
                                            and thinking_content
                                        ):
                                            stream_thinking(thinking_content)
                                        elif (
                                            current_phase == "answer" and answer_content
                                        ):
                                            pass  # Will be displayed at end

                                        if (
                                            phase == "answer"
                                            and current_phase == "think"
                                        ):
                                            print_response_start()

                                        current_phase = phase

                                    # Accumulate content
                                    if content:
                                        if phase == "think":
                                            thinking_content += content
                                        else:
                                            answer_content += content

                                    if status == "finished" and phase == "answer":
                                        break

                        except json.JSONDecodeError:
                            pass

                # Display final answer with live streaming effect
                if answer_content:
                    stream_live(iter([answer_content]))

                return answer_content

        except Exception as e:
            print_status(f"Error during chat: {e}", "red")
            return None

    def new_conversation(self):
        """Start a fresh conversation"""
        self.conversation_id = None
        self.parent_id = None
        print_status("Ready for new conversation", "cyan")

    def send_message(self, prompt: str, system_prompt: str = None) -> str:
        """
        Send a message and return the response as a string (no console output).
        Used for programmatic access (e.g., CrewAI integration).
        
        Args:
            prompt: The user message to send
            system_prompt: Optional system prompt to prepend
            
        Returns:
            The complete response as a string
        """
        if not self.cookies:
            return "Error: No cookies found - please login first"

        if not self.conversation_id:
            if not self._create_conversation():
                return "Error: Failed to create session"

        headers = self._get_headers()

        message_fid = str(uuid.uuid4())
        child_id = str(uuid.uuid4())
        current_timestamp = int(time.time())

        # Prepend system prompt to user message if provided
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"[System Instructions: {system_prompt}]\n\nUser Request: {prompt}"

        feature_config = {
            "thinking_enabled": self.thinking_enabled,
            "output_schema": "phase",
            "research_mode": "normal",
        }

        if self.thinking_enabled:
            feature_config["thinking_budget"] = self.thinking_budget

        payload = {
            "stream": True,
            "version": "2.1",
            "incremental_output": True,
            "chat_id": self.conversation_id,
            "chat_mode": "normal",
            "model": "qwen3-max-2025-10-30",
            "parent_id": self.parent_id,
            "messages": [
                {
                    "fid": message_fid,
                    "parentId": self.parent_id,
                    "childrenIds": [child_id],
                    "role": "user",
                    "content": full_prompt,
                    "user_action": "chat",
                    "files": [],
                    "timestamp": current_timestamp,
                    "models": ["qwen3-max-2025-10-30"],
                    "chat_type": "t2t",
                    "feature_config": feature_config,
                    "extra": {"meta": {"subChatType": "t2t"}},
                    "sub_chat_type": "t2t",
                    "parent_id": self.parent_id,
                }
            ],
            "timestamp": current_timestamp,
        }

        try:
            with self.client.stream(
                "POST",
                f"{self.config.BASE_URL}/api/v2/chat/completions?chat_id={self.conversation_id}",
                headers=headers,
                cookies=self.cookies,
                json=payload,
            ) as resp:
                if resp.status_code != 200:
                    return f"Error: Request failed with status {resp.status_code}"

                answer_content = ""

                for line in resp.iter_lines():
                    if not line:
                        continue

                    if line.startswith("data:"):
                        json_str = line[5:].strip()
                        if not json_str or json_str == "[DONE]":
                            continue

                        try:
                            data = json.loads(json_str)

                            if "response.created" in data:
                                created_info = data["response.created"]
                                if "response_id" in created_info:
                                    self.parent_id = created_info["response_id"]
                                continue

                            if "choices" in data:
                                for choice in data["choices"]:
                                    delta = choice.get("delta", {})
                                    content = delta.get("content", "")
                                    phase = delta.get("phase", "answer")

                                    if content and phase == "answer":
                                        answer_content += content

                        except json.JSONDecodeError:
                            pass

                return answer_content

        except Exception as e:
            return f"Error: {str(e)}"
